from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.chat.models import Room


class IsRoomParticipant(BasePermission):
    """대화방 참여자인지 확인하는 권한 클래스."""

    message = "대화방에 참여하지 않은 사용자입니다."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """뷰 레벨 권한 확인.

        URL kwargs에서 room_id를 추출하여 참여자 확인.
        Room이 존재하지 않으면 False 반환 (404는 뷰에서 처리).
        """
        room_id = view.kwargs.get("room_id")
        if not room_id:
            return False

        try:
            room = Room.objects.get(pk=room_id)
        except Room.DoesNotExist:
            return False

        # view에 room 캐싱 (중복 쿼리 방지)
        view.room = room  # type: ignore[attr-defined]

        return room.is_participant(request.user)
