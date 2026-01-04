from datetime import date
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, View

import structlog

from apps.chat.constants import MAX_SYNC_MESSAGES, MESSAGES_PER_PAGE
from apps.chat.models import Message, Room
from apps.users.models import User

logger = structlog.get_logger(__name__)


class RoomListView(LoginRequiredMixin, ListView):
    """대화 목록 뷰"""

    model = Room
    template_name = "chat/room.html"
    context_object_name = "rooms"
    paginate_by = 20

    def get_queryset(self) -> QuerySet[Room]:
        return (
            Room.objects.get_by_user(self.request.user)
            .prefetch_related("participants")
            .with_latest_message()
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["today"] = date.today()
        context["selected_room"] = None
        context["chat_messages"] = []
        return context


class RoomDetailView(LoginRequiredMixin, DetailView):
    """대화 상세 뷰"""

    model = Room
    template_name = "chat/room.html"
    context_object_name = "selected_room"

    def get_object(self, queryset: QuerySet[Room] | None = None) -> Room:
        room = super().get_object(queryset)
        if not room.is_participant(self.request.user):
            logger.warning(
                "room_access_denied",
                reason="not_participant",
                room_id=room.pk,
                user_id=self.request.user.pk,
            )
            raise PermissionDenied("대화방에 참여하지 않은 사용자입니다.")
        return room

    def get_queryset(self) -> QuerySet[Room]:
        return super().get_queryset().prefetch_related("participants")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        room = self.object
        user = self.request.user

        # 채팅방 목록 추가
        context["rooms"] = Room.objects.get_by_user(user).with_latest_message()
        context["today"] = date.today()

        # 메시지 목록 (최신 N개만 로드)
        chat_messages = Message.objects.get_latest_messages(room, MAX_SYNC_MESSAGES)
        context["chat_messages"] = chat_messages

        # 무한 스크롤을 위한 추가 컨텍스트
        total_count = Message.objects.filter(room=room).count()
        context["has_more_messages"] = total_count > MAX_SYNC_MESSAGES
        context["oldest_message_id"] = chat_messages[0].pk if chat_messages else None

        # 1:1 대화인 경우 상대방 정보 (prefetch된 participants에서 조회)
        if room.is_direct:
            other_user = room.get_other_participant(user)
            context["other_user"] = other_user
            context["display_name"] = other_user.name if other_user else "알 수 없음"
        else:
            context["display_name"] = room.name

        return context


class NewConversationView(LoginRequiredMixin, View):
    """새 대화 시작 뷰."""

    template_name = "chat/new_conversation.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        query = request.GET.get("q", "")
        users = []

        if query:
            users = (
                User.objects.filter(
                    Q(name__icontains=query) | Q(email__icontains=query)
                )
                .exclude(pk=request.user.pk)
                .order_by("name")[:20]
            )

        return render(request, self.template_name, {"query": query, "users": users})

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user_id = request.POST.get("user_id")
        if not user_id:
            logger.warning(
                "new_conversation_failed",
                reason="user_id_missing",
                user_id=request.user.pk,
            )
            return redirect("chat:new_conversation")

        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.warning(
                "new_conversation_failed",
                reason="invalid_user_id",
                user_id=request.user.pk,
                target_user_id=user_id,
            )
            return redirect("chat:new_conversation")

        other_user = get_object_or_404(User, pk=user_id_int)
        room = Room.objects.get_or_create_direct(request.user, other_user)

        logger.info(
            "new_conversation_started",
            room_id=room.pk,
            user_id=request.user.pk,
            other_user_id=other_user.pk,
        )

        return redirect("chat:room_detail", pk=room.pk)


class MessageListAPIView(LoginRequiredMixin, View):
    """메시지 목록 API (Cursor 기반 Pagination)"""

    def get(self, request: HttpRequest, room_id: int) -> JsonResponse:
        """메시지를 조회한다.

        Query Parameters (상호 배타적):
            before: 이 ID 이전의 메시지 조회 (스크롤 업)
            after: 이 ID 이후의 메시지 조회 (스크롤 다운)
            around: 이 ID 전후의 메시지 조회 (검색)
            limit: 조회 개수 (기본값: MESSAGES_PER_PAGE)
        """
        # Room 조회 및 권한 확인
        try:
            room = Room.objects.get(pk=room_id)
        except Room.DoesNotExist:
            return JsonResponse({"error": "Room not found"}, status=404)

        if not room.is_participant(request.user):
            logger.warning(
                "message_api_access_denied",
                reason="not_participant",
                room_id=room_id,
                user_id=request.user.pk,
            )
            return JsonResponse({"error": "Forbidden"}, status=403)

        # 파라미터 파싱
        before = request.GET.get("before")
        after = request.GET.get("after")
        around = request.GET.get("around")
        limit = min(
            int(request.GET.get("limit", MESSAGES_PER_PAGE)),
            MESSAGES_PER_PAGE * 2,  # 최대 2배까지 허용
        )

        # 파라미터 검증 (정확히 하나만 필요)
        params = [before, after, around]
        param_count = sum(1 for p in params if p is not None)
        if param_count != 1:
            return JsonResponse(
                {"error": "Exactly one of before, after, or around parameter required"},
                status=400,
            )

        # 파라미터 변환 및 분기
        try:
            if before:
                cursor_id = int(before)
                return self._get_messages_before(room, cursor_id, limit, request.user)
            elif after:
                cursor_id = int(after)
                return self._get_messages_after(room, cursor_id, limit, request.user)
            else:  # around
                cursor_id = int(around)  # type: ignore[arg-type]
                return self._get_messages_around(room, cursor_id, limit, request.user)
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid cursor"}, status=400)

    def _get_messages_before(
        self, room: Room, cursor_id: int, limit: int, user: User
    ) -> JsonResponse:
        """이전 메시지 조회 (스크롤 업)."""
        messages, has_more = Message.objects.get_messages_before(
            room=room, cursor_id=cursor_id, limit=limit
        )

        logger.info(
            "messages_loaded",
            direction="before",
            room_id=room.pk,
            user_id=user.pk,
            cursor_id=cursor_id,
            count=len(messages),
            has_more=has_more,
        )

        return JsonResponse({
            "messages": self._serialize_messages(messages),
            "has_more": has_more,
            "next_cursor": messages[0].pk if messages and has_more else None,
        })

    def _get_messages_after(
        self, room: Room, cursor_id: int, limit: int, user: User
    ) -> JsonResponse:
        """이후 메시지 조회 (스크롤 다운)."""
        messages, has_more = Message.objects.get_messages_after(
            room=room, cursor_id=cursor_id, limit=limit
        )

        logger.info(
            "messages_loaded",
            direction="after",
            room_id=room.pk,
            user_id=user.pk,
            cursor_id=cursor_id,
            count=len(messages),
            has_more=has_more,
        )

        return JsonResponse({
            "messages": self._serialize_messages(messages),
            "has_more": has_more,
            "next_cursor": messages[-1].pk if messages and has_more else None,
        })

    def _get_messages_around(
        self, room: Room, cursor_id: int, limit: int, user: User
    ) -> JsonResponse:
        """전후 메시지 조회 (검색용)."""
        messages, has_more_before, has_more_after = Message.objects.get_messages_around(
            room=room, cursor_id=cursor_id, limit=limit
        )

        logger.info(
            "messages_loaded",
            direction="around",
            room_id=room.pk,
            user_id=user.pk,
            cursor_id=cursor_id,
            count=len(messages),
            has_more_before=has_more_before,
            has_more_after=has_more_after,
        )

        return JsonResponse({
            "messages": self._serialize_messages(messages),
            "has_more_before": has_more_before,
            "has_more_after": has_more_after,
            "next_cursor_before": messages[0].pk if messages and has_more_before else None,
            "next_cursor_after": messages[-1].pk if messages and has_more_after else None,
            "target_message_id": cursor_id,
        })

    def _serialize_messages(self, messages: list[Message]) -> list[dict]:
        """메시지 직렬화."""
        return [
            {
                "id": msg.pk,
                "content": msg.content,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender.name if msg.sender else "알 수 없음",
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]
