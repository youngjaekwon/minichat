import structlog
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import Message, MessageRead, Room
from apps.chat.permissions import IsRoomParticipant
from apps.chat.serializers import (
    MessageDirection,
    MessageListParamsSerializer,
    MessageSearchParamsSerializer,
    MessageSerializer,
    RoomListParamsSerializer,
    RoomSearchParamsSerializer,
    RoomSearchResultSerializer,
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
    GET /chat/api/rooms/?cursor={datetime}&limit={limit}

    Query Parameters:
        cursor: 커서 기준 시간 (ISO 8601)
        limit: 조회 개수

    Returns:
        rooms: 채팅방 목록
            - id: 대화방 ID
            - display_name: 표시 이름
            - last_message_preview: 마지막 메시지 미리보기
            - updated_at: 마지막 업데이트 시간
            - is_today: 오늘 업데이트 여부
        has_more: 추가 데이터 존재 여부
        next_cursor: 다음 페이지 커서 시간
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """채팅방 목록을 조회한다."""
        params = RoomListParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        cursor = params.validated_data.get("cursor")
        limit = params.validated_data["limit"]

        rooms, has_more, next_cursor = Room.objects.get_by_user_paginated(
            request.user,
            cursor=cursor,
            limit=limit,
        )

        # 모든 방의 안읽은 메시지 수를 조회
        unread_counts = MessageRead.objects.get_unread_counts_for_rooms(
            rooms, request.user
        )

        serializer = RoomSerializer(
            rooms,
            many=True,
            context={
                "user": request.user,
                "unread_counts": unread_counts,
            },
        )

        logger.info(
            "rooms_loaded",
            user_id=request.user.pk,
            count=len(rooms),
            has_more=has_more,
        )

        return Response(
            {
                "rooms": serializer.data,
                "has_more": has_more,
                "next_cursor": next_cursor,
            }
        )


class RoomSearchAPIView(APIView):
    """대화방 검색 API.

    사용자가 참여 중인 대화방의 메시지에서 검색어를 찾고,
    일치하는 메시지가 있는 대화방 목록을 반환한다.

    GET /chat/api/rooms/search/?q=검색어
    GET /chat/api/rooms/search/?q=검색어&cursor={datetime}&limit={limit}

    Query Parameters:
        q: 검색어 (필수, 최소 2자)
        cursor: 커서 기준 시간 (ISO 8601)
        limit: 조회 개수

    Returns:
        rooms: 일치하는 메시지가 있는 대화방 목록
            - id: 대화방 ID
            - display_name: 표시 이름
            - matched_message_preview: 일치하는 메시지 미리보기
        has_more: 추가 데이터 존재 여부
        next_cursor: 다음 페이지 커서 시간
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """대화방을 검색한다."""
        params = RoomSearchParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        query = params.validated_data["q"]
        cursor = params.validated_data.get("cursor")
        limit = params.validated_data["limit"]

        results, has_more, next_cursor = Room.objects.search_by_message(
            request.user,
            query,
            cursor=cursor,
            limit=limit,
        )

        serializer = RoomSearchResultSerializer(results, many=True)

        logger.info(
            "rooms_searched",
            user_id=request.user.pk,
            query=query,
            result_count=len(results),
            has_more=has_more,
        )

        return Response(
            {
                "rooms": serializer.data,
                "has_more": has_more,
                "next_cursor": next_cursor,
            }
        )
