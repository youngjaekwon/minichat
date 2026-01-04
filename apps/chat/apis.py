import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import Message, Room
from apps.chat.permissions import IsRoomParticipant
from apps.chat.serializers import (
    MessageDirection,
    MessageListParamsSerializer,
    MessageSerializer,
)

logger = structlog.get_logger(__name__)


class MessageListAPIView(APIView):
    """메시지 목록 API (Cursor 기반 Pagination).

    Query Parameters:
        direction: 조회 방향 (before|after|around)
        cursor: 기준 메시지 ID
        limit: 조회 개수 (기본값: MESSAGES_PER_PAGE)
    """

    permission_classes = [IsAuthenticated, IsRoomParticipant]

    # IsRoomParticipant에서 캐싱됨
    room: Room

    def get(self, request: Request, room_id: int) -> Response:
        """메시지를 조회한다."""
        # Room이 없으면 404 (permission에서 캐싱 실패)
        if not hasattr(self, "room"):
            return Response(
                {"detail": "Room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serializer로 파라미터 검증
        params = MessageListParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        direction = data["direction"]
        cursor = data["cursor"]
        limit = data["limit"]

        # 분기 처리
        if direction == MessageDirection.BEFORE:
            return self._get_messages_before(cursor, limit)
        elif direction == MessageDirection.AFTER:
            return self._get_messages_after(cursor, limit)
        else:  # AROUND
            return self._get_messages_around(cursor, limit)

    def _get_messages_before(self, cursor_id: int, limit: int) -> Response:
        """이전 메시지 조회 (스크롤 업)."""
        messages, has_more = Message.objects.get_messages_before(
            room=self.room, cursor_id=cursor_id, limit=limit
        )

        logger.info(
            "messages_loaded",
            direction="before",
            room_id=self.room.pk,
            user_id=self.request.user.pk,
            cursor_id=cursor_id,
            count=len(messages),
            has_more=has_more,
        )

        return Response(
            {
                "messages": MessageSerializer(messages, many=True).data,
                "has_more": has_more,
                "next_cursor": messages[0].pk if messages and has_more else None,
            }
        )

    def _get_messages_after(self, cursor_id: int, limit: int) -> Response:
        """이후 메시지 조회 (스크롤 다운)."""
        messages, has_more = Message.objects.get_messages_after(
            room=self.room, cursor_id=cursor_id, limit=limit
        )

        logger.info(
            "messages_loaded",
            direction="after",
            room_id=self.room.pk,
            user_id=self.request.user.pk,
            cursor_id=cursor_id,
            count=len(messages),
            has_more=has_more,
        )

        return Response(
            {
                "messages": MessageSerializer(messages, many=True).data,
                "has_more": has_more,
                "next_cursor": messages[-1].pk if messages and has_more else None,
            }
        )

    def _get_messages_around(self, cursor_id: int, limit: int) -> Response:
        """전후 메시지 조회 (검색용)."""
        messages, has_more_before, has_more_after = Message.objects.get_messages_around(
            room=self.room, cursor_id=cursor_id, limit=limit
        )

        logger.info(
            "messages_loaded",
            direction="around",
            room_id=self.room.pk,
            user_id=self.request.user.pk,
            cursor_id=cursor_id,
            count=len(messages),
            has_more_before=has_more_before,
            has_more_after=has_more_after,
        )

        return Response(
            {
                "messages": MessageSerializer(messages, many=True).data,
                "has_more_before": has_more_before,
                "has_more_after": has_more_after,
                "next_cursor_before": messages[0].pk
                if messages and has_more_before
                else None,
                "next_cursor_after": messages[-1].pk
                if messages and has_more_after
                else None,
                "target_message_id": cursor_id,
            }
        )
