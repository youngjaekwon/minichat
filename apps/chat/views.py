from datetime import date
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, View

from apps.chat.forms import MessageForm
from apps.chat.models import Message, Room
from apps.users.models import User


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
        context["form"] = MessageForm()
        return context


class RoomDetailView(LoginRequiredMixin, DetailView):
    """대화 상세 뷰"""

    model = Room
    template_name = "chat/room.html"
    context_object_name = "selected_room"

    def get_object(self, queryset: QuerySet[Room] | None = None) -> Room:
        room = super().get_object(queryset)
        if not room.is_participant(self.request.user):
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

        # 메시지 목록
        context["chat_messages"] = Message.objects.get_by_room(room)
        context["form"] = MessageForm()

        # 1:1 대화인 경우 상대방 정보 (prefetch된 participants에서 조회)
        if room.is_direct:
            other_user = room.get_other_participant(user)
            context["other_user"] = other_user
            context["display_name"] = other_user.name if other_user else "알 수 없음"
        else:
            context["display_name"] = room.name

        return context


class SendMessageView(LoginRequiredMixin, View):
    """메시지 전송 뷰."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        room = get_object_or_404(Room, pk=pk)

        if not room.is_participant(request.user):
            raise PermissionDenied("대화방에 참여하지 않은 사용자입니다.")

        form = MessageForm(request.POST)
        if form.is_valid():
            form.save(room=room, sender=request.user)
        else:
            messages.error(request, "메시지를 입력해주세요.")

        return redirect("chat:room_detail", pk=room.pk)


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
            return redirect("chat:new_conversation")

        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            return redirect("chat:new_conversation")

        other_user = get_object_or_404(User, pk=user_id_int)
        room = Room.objects.get_or_create_direct(request.user, other_user)

        return redirect("chat:room_detail", pk=room.pk)
