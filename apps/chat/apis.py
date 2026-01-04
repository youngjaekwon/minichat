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
    MessageSearchParamsSerializer,
    MessageSerializer,
    RoomSerializer,
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
        cursor = data.get("cursor")
        limit = data["limit"]

        # cursor가 없으면 최신 메시지 조회 (초기 로딩)
        if cursor is None:
            return self._get_initial_messages(limit)

        # 분기 처리
        if direction == MessageDirection.BEFORE:
            return self._get_messages_before(cursor, limit)
        elif direction == MessageDirection.AFTER:
            return self._get_messages_after(cursor, limit)
        else:  # AROUND
            return self._get_messages_around(cursor, limit)

    def _get_initial_messages(self, limit: int) -> Response:
        """초기 메시지 조회 (최신 N개)."""
        messages = Message.objects.get_latest_messages(room=self.room, limit=limit)
        total_count = Message.objects.filter(room=self.room).count()
        has_more = total_count > len(messages)

        logger.info(
            "messages_loaded",
            direction="initial",
            room_id=self.room.pk,
            user_id=self.request.user.pk,
            count=len(messages),
            has_more_before=has_more,
            has_more_after=False,
        )

        return Response(
            {
                "messages": MessageSerializer(messages, many=True).data,
                "has_more_before": has_more,
                "has_more_after": False,  # 최신 메시지이므로 이후 없음
                "next_cursor_before": messages[0].pk if messages and has_more else None,
                "next_cursor_after": None,
            }
        )

    def _get_messages_before(self, cursor_id: int, limit: int) -> Response:
        """이전 메시지 조회 (스크롤 업)."""
        messages, has_more_before = Message.objects.get_messages_before(
            room=self.room, cursor_id=cursor_id, limit=limit
        )
        # cursor_id 이후에 메시지가 있는지 확인
        has_more_after = Message.objects.filter(
            room=self.room, pk__gt=cursor_id
        ).exists()

        logger.info(
            "messages_loaded",
            direction="before",
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
            }
        )

    def _get_messages_after(self, cursor_id: int, limit: int) -> Response:
        """이후 메시지 조회 (스크롤 다운)."""
        messages, has_more_after = Message.objects.get_messages_after(
            room=self.room, cursor_id=cursor_id, limit=limit
        )
        # cursor_id 이전에 메시지가 있는지 확인
        has_more_before = Message.objects.filter(
            room=self.room, pk__lt=cursor_id
        ).exists()

        logger.info(
            "messages_loaded",
            direction="after",
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
            }
        )


class MessageSearchAPIView(APIView):
    """메시지 검색 API.

    Query Parameters:
        q: 검색어 (최소 2자)

    Returns:
        message_ids: 검색 결과 메시지 ID 목록 (시간순 정렬)
        total: 총 검색 결과 수
    """

    permission_classes = [IsAuthenticated, IsRoomParticipant]

    # IsRoomParticipant에서 캐싱됨
    room: Room

    def get(self, request: Request, room_id: int) -> Response:
        """메시지를 검색한다."""
        if not hasattr(self, "room"):
            return Response(
                {"detail": "Room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        params = MessageSearchParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        query = params.validated_data["q"]

        message_ids = list(
            Message.objects.get_queryset()
            .for_room(self.room)
            .search(query)
            .ordered_by_created_asc()
            .values_list("pk", flat=True)
        )

        logger.info(
            "messages_searched",
            room_id=self.room.pk,
            user_id=self.request.user.pk,
            query=query,
            result_count=len(message_ids),
        )

        return Response(
            {
                "message_ids": message_ids,
                "total": len(message_ids),
            }
        )


class RoomListAPIView(APIView):
    """채팅방 목록 API.

    사용자가 참여 중인 채팅방 목록을 반환한다.

    GET /chat/api/rooms/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """채팅방 목록을 조회한다."""
        rooms = (
            Room.objects.get_by_user(request.user)
            .prefetch_related("participants")
            .with_latest_message()
        )

        serializer = RoomSerializer(
            rooms,
            many=True,
            context={"user": request.user},
        )
        data = serializer.data

        logger.info(
            "rooms_loaded",
            user_id=request.user.pk,
            count=len(data),
        )

        return Response({"rooms": data})
