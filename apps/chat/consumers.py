from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import structlog
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from pydantic import ValidationError

from apps.chat.constants import (
    CLOSE_CODE_FORBIDDEN,
    CLOSE_CODE_NOT_FOUND,
    CLOSE_CODE_UNAUTHORIZED,
    ERROR_EMPTY_MESSAGE,
    ERROR_INVALID_FORMAT,
    MAX_SYNC_MESSAGES,
)
from apps.chat.messages import (
    ChatReceivedMessage,
    ChatSendMessage,
    ErrorMessage,
    IncomingMessageAdapter,
    MessageAckMessage,
    MessagePayload,
)
from apps.chat.models import Message, Room
from apps.users.models import User

logger = structlog.get_logger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket Consumer for chat rooms."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.room_id: int | None = None
        self.room: Room | None = None
        self.room_group_name: str | None = None
        self.user: User | None = None
        self.last_message_id: int | None = None

    async def connect(self) -> None:
        """WebSocket 연결 시 호출.

        1. 인증 확인
        2. Room 존재 여부 확인
        3. 참여자 검증
        4. Channel Layer 그룹 참가
        5. 누락 메시지 동기화
        """
        self.user = self.scope.get("user")

        # 1. 인증 확인
        if not self.user or not self.user.is_authenticated:
            logger.warning(
                "websocket_connection_rejected",
                reason="unauthorized",
            )
            await self.close(code=CLOSE_CODE_UNAUTHORIZED)
            return

        # 2. Room ID 추출
        self.room_id = self.scope["url_route"]["kwargs"].get("room_id")
        if not self.room_id:
            logger.warning(
                "websocket_connection_rejected",
                reason="room_id_missing",
                user_id=self.user.pk,
            )
            await self.close(code=CLOSE_CODE_NOT_FOUND)
            return

        # 3. Room 존재 여부 확인
        self.room = await self._get_room(self.room_id)
        if not self.room:
            logger.warning(
                "websocket_connection_rejected",
                reason="room_not_found",
                room_id=self.room_id,
                user_id=self.user.pk,
            )
            await self.close(code=CLOSE_CODE_NOT_FOUND)
            return

        # 4. 참여자 검증
        is_participant = await self._is_participant(self.room, self.user)
        if not is_participant:
            logger.warning(
                "websocket_connection_rejected",
                reason="not_participant",
                room_id=self.room_id,
                user_id=self.user.pk,
            )
            await self.close(code=CLOSE_CODE_FORBIDDEN)
            return

        # 5. Channel Layer 그룹 참가
        self.room_group_name = f"chat_room_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # 연결 수락
        await self.accept()

        logger.info(
            "websocket_connected",
            room_id=self.room_id,
            user_id=self.user.pk,
        )

        # 6. 누락 메시지 동기화 (쿼리 파라미터에서 last_message_id 추출)
        query_string = self.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        last_message_id_param = query_params.get("last_message_id", [None])[0]

        if last_message_id_param:
            try:
                self.last_message_id = int(last_message_id_param)
                await self._sync_missed_messages()
            except ValueError:
                logger.warning(
                    "message_sync_failed",
                    reason="invalid_last_message_id",
                    room_id=self.room_id,
                    user_id=self.user.pk,
                    last_message_id_param=last_message_id_param,
                )

    async def disconnect(self, close_code: int) -> None:
        """WebSocket 연결 종료 시 호출."""
        logger.info(
            "websocket_disconnected",
            room_id=self.room_id,
            user_id=self.user.pk if self.user else None,
            close_code=close_code,
        )

        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data: str | None = None, **kwargs: Any) -> None:
        """클라이언트로부터 메시지 수신 시 호출."""
        if not text_data:
            logger.warning(
                "message_received_empty",
                room_id=self.room_id,
                user_id=self.user.pk if self.user else None,
            )
            return

        try:
            message = IncomingMessageAdapter.validate_json(text_data)
        except ValidationError:
            logger.warning(
                "message_validation_failed",
                reason="invalid_json_format",
                room_id=self.room_id,
                user_id=self.user.pk if self.user else None,
                text_data=text_data,
            )
            await self._send_error(
                ERROR_INVALID_FORMAT, "유효하지 않은 JSON 형식입니다."
            )
            return

        await self._handle_chat_message(message)

    async def _handle_chat_message(self, msg: ChatSendMessage) -> None:
        """채팅 메시지 처리."""
        content = msg.content.strip()

        # 빈 메시지 검증
        if not content:
            logger.warning(
                "message_validation_failed",
                reason="empty_message",
                room_id=self.room_id,
                user_id=self.user.pk,
            )
            await self._send_error(ERROR_EMPTY_MESSAGE, "메시지 내용이 비어있습니다.")
            return

        # DB에 메시지 저장
        message = await self._create_message(content)

        logger.info(
            "message_sent",
            room_id=self.room_id,
            user_id=self.user.pk,
            message_id=message.pk,
        )

        # 그룹에 메시지 브로드캐스트
        broadcast_msg = ChatReceivedMessage(
            message=MessagePayload(
                id=message.pk,
                content=message.content,
                sender_id=self.user.pk,
                sender_name=self.user.name,
                created_at=message.created_at.isoformat(),
            )
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            broadcast_msg.model_dump(),
        )

        # ACK 응답 (전송자에게만)
        if msg.client_id:
            ack_msg = MessageAckMessage(
                client_id=msg.client_id,
                message_id=message.pk,
            )
            await self.send(text_data=ack_msg.model_dump_json())

    async def chat_message(self, event: dict[str, Any]) -> None:
        """Channel Layer에서 메시지 수신 후 클라이언트에 전송."""
        msg = ChatReceivedMessage(**event)
        await self.send(text_data=msg.model_dump_json())

    async def _send_error(self, code: str, message: str) -> None:
        """에러 응답 전송."""
        error_msg = ErrorMessage(code=code, message=message)
        await self.send(text_data=error_msg.model_dump_json())

    async def _sync_missed_messages(self) -> None:
        """재연결 시 누락된 메시지 동기화."""
        if not self.last_message_id or not self.room:
            return

        missed_messages = await self._get_missed_messages(
            self.room, self.last_message_id
        )

        if missed_messages:
            logger.info(
                "message_sync_started",
                room_id=self.room_id,
                user_id=self.user.pk if self.user else None,
                last_message_id=self.last_message_id,
                sync_count=len(missed_messages),
            )

        for message in missed_messages:
            sync_msg = ChatReceivedMessage(
                message=MessagePayload(
                    id=message.pk,
                    content=message.content,
                    sender_id=message.sender_id,
                    sender_name=message.sender.name if message.sender else "알 수 없음",
                    created_at=message.created_at.isoformat(),
                )
            )
            await self.send(text_data=sync_msg.model_dump_json())

    # Database helper methods (sync_to_async wrapped)

    @sync_to_async
    def _get_room(self, room_id: int) -> Room | None:
        """Room을 조회한다."""
        try:
            return Room.objects.get(pk=room_id)
        except Room.DoesNotExist:
            return None

    @sync_to_async
    def _is_participant(self, room: Room, user: User) -> bool:
        """사용자가 대화방 참여자인지 확인한다."""
        return room.is_participant(user)

    @sync_to_async
    def _create_message(self, content: str) -> Message:
        """새 메시지를 생성한다."""
        return Message.objects.create_message(
            room=self.room,
            sender=self.user,
            content=content,
        )

    @sync_to_async
    def _get_missed_messages(self, room: Room, last_message_id: int) -> list[Message]:
        """누락된 메시지를 조회한다 (최대 MAX_SYNC_MESSAGES개)."""
        return list(
            Message.objects.filter(room=room, pk__gt=last_message_id)
            .select_related("sender")
            .order_by("created_at")[:MAX_SYNC_MESSAGES]
        )
