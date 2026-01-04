"""
Celery tasks for chat application.
"""

from __future__ import annotations

import structlog
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from apps.chat.messages import (
    SidebarRoomPayload,
    SidebarUpdateMessage,
)
from apps.chat.models import MessageRead, Room
from apps.users.models import User

logger = structlog.get_logger(__name__)


@shared_task(ignore_result=True)
def save_read_status(
    room_id: int,
    user_id: int,
    message_ids: list[int],
) -> None:
    """읽음 상태를 DB에 비동기 저장한다.

    Args:
        room_id: 대화방 ID
        user_id: 읽은 사용자 ID
        message_ids: 읽음 처리할 메시지 ID 목록
    """
    if not message_ids:
        return

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(
            "save_read_status_failed",
            reason="user_not_found",
            user_id=user_id,
        )
        return

    # 읽음 기록 생성
    read_records = [MessageRead(message_id=msg_id, user=user) for msg_id in message_ids]

    if read_records:
        MessageRead.objects.bulk_create(read_records, ignore_conflicts=True)
        logger.info(
            "read_status_saved",
            room_id=room_id,
            user_id=user_id,
            message_count=len(message_ids),
        )


@shared_task(ignore_result=True)
def broadcast_sidebar_update(
    room_id: int,
    participant_ids: list[int],
    last_message_content: str | None = None,
    last_message_time: str | None = None,
) -> None:
    """사이드바 업데이트를 참여자에게 비동기 브로드캐스트한다.

    Args:
        room_id: 대화방 ID
        participant_ids: 참여자 ID 목록
        last_message_content: 최신 메시지 내용
        last_message_time: 최신 메시지 시간 (ISO 8601)
    """
    if not participant_ids:
        return

    # Room을 조회
    try:
        room = Room.objects.get(pk=room_id)
    except Room.DoesNotExist:
        logger.warning(
            "broadcast_sidebar_update_failed",
            reason="room_not_found",
            room_id=room_id,
        )
        return

    # 모든 참여자의 안읽은 메시지 수를 조회
    unread_counts = MessageRead.objects.get_unread_counts_for_users(
        room, participant_ids
    )

    channel_layer = get_channel_layer()

    # 각 참여자에게 개인화된 안읽은 메시지 수와 함께 전송
    for user_id in participant_ids:
        unread_count = unread_counts.get(user_id, 0)

        sidebar_msg = SidebarUpdateMessage(
            room=SidebarRoomPayload(
                room_id=room_id,
                last_message=last_message_content[:50]
                if last_message_content
                else None,
                last_message_time=last_message_time,
                unread_count=unread_count,
            )
        )

        group_name = f"user_chat_rooms_{user_id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            sidebar_msg.model_dump(),
        )

    logger.info(
        "sidebar_update_broadcasted",
        room_id=room_id,
        participant_count=len(participant_ids),
    )


@shared_task(ignore_result=True)
def broadcast_sidebar_unread_update(
    room_id: int,
    user_id: int,
) -> None:
    """특정 사용자의 사이드바 안읽은 수만 업데이트한다.

    읽음 처리 후 본인의 사이드바 업데이트에 사용.

    Args:
        room_id: 대화방 ID
        user_id: 사용자 ID
    """
    channel_layer = get_channel_layer()

    try:
        room = Room.objects.get(pk=room_id)
        user = User.objects.get(pk=user_id)
        unread_count = MessageRead.objects.get_unread_count(room, user)

        # 최신 메시지 정보 조회
        last_message = room.get_last_message()
        last_message_content = last_message.get_preview() if last_message else None
        last_message_time = (
            last_message.created_at.isoformat() if last_message else None
        )
    except (Room.DoesNotExist, User.DoesNotExist):
        return

    sidebar_msg = SidebarUpdateMessage(
        room=SidebarRoomPayload(
            room_id=room_id,
            last_message=last_message_content,
            last_message_time=last_message_time,
            unread_count=unread_count,
        )
    )

    group_name = f"user_chat_rooms_{user_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        sidebar_msg.model_dump(),
    )
