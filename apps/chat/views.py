from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, View

import structlog

from apps.chat.models import Room
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
        context["selected_room"] = None
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
