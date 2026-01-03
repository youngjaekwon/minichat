"""
Chat 뷰 테스트
"""

from django.urls import reverse

import pytest

from apps.chat.models import Message, Room
from tests.factories import MessageFactory, RoomFactory, UserFactory


@pytest.mark.django_db
class TestRoomListView:
    """대화 목록 뷰 테스트."""

    def test_requires_login(self, client):
        """로그인 필수 테스트."""
        url = reverse("chat:room_list")
        response = client.get(url)

        assert response.status_code == 302
        assert "login" in response.url

    def test_shows_rooms(self, client):
        """대화 목록 표시 테스트."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        client.force_login(user)
        response = client.get(reverse("chat:room_list"))

        assert response.status_code == 200
        assert room in response.context["rooms"]

    def test_shows_only_user_rooms(self, client):
        """참여 중인 대화방만 표시 테스트."""
        user = UserFactory()
        other_user1 = UserFactory()
        other_user2 = UserFactory()

        my_room = RoomFactory(created_by=user, participants=[other_user1])
        RoomFactory(created_by=other_user1, participants=[other_user2])

        client.force_login(user)
        response = client.get(reverse("chat:room_list"))

        rooms = list(response.context["rooms"])
        assert len(rooms) == 1
        assert my_room in rooms

    def test_empty_state(self, client):
        """대화 없는 상태 테스트."""
        user = UserFactory()

        client.force_login(user)
        response = client.get(reverse("chat:room_list"))

        assert response.status_code == 200
        assert len(response.context["rooms"]) == 0


@pytest.mark.django_db
class TestRoomDetailView:
    """대화 상세 뷰 테스트."""

    def test_requires_login(self, client):
        """로그인 필수 테스트."""
        room = RoomFactory()
        url = reverse("chat:room_detail", args=[room.pk])
        response = client.get(url)

        assert response.status_code == 302
        assert "login" in response.url

    def test_shows_messages(self, client):
        """메시지 목록 표시 테스트."""
        user = UserFactory()
        room = RoomFactory(created_by=user)
        message = MessageFactory(room=room, sender=user, content="테스트 메시지")

        client.force_login(user)
        response = client.get(reverse("chat:room_detail", args=[room.pk]))

        assert response.status_code == 200
        assert message in response.context["chat_messages"]

    def test_non_participant_denied(self, client):
        """비참여자 접근 차단 테스트."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=other_user)

        client.force_login(user)
        response = client.get(reverse("chat:room_detail", args=[room.pk]))

        assert response.status_code == 403

    def test_shows_other_user_info(self, client):
        """상대방 정보 표시 테스트."""
        user = UserFactory()
        other_user = UserFactory(name="김철수", job_title="개발자")
        room = RoomFactory(created_by=user, participants=[other_user])

        client.force_login(user)
        response = client.get(reverse("chat:room_detail", args=[room.pk]))

        assert response.context["other_user"] == other_user


@pytest.mark.django_db
class TestSendMessageView:
    """메시지 전송 뷰 테스트."""

    def test_requires_login(self, client):
        """로그인 필수 테스트."""
        room = RoomFactory()
        url = reverse("chat:send_message", args=[room.pk])
        response = client.post(url, {"content": "test"})

        assert response.status_code == 302
        assert "login" in response.url

    def test_send_message_success(self, client):
        """메시지 전송 성공 테스트."""
        user = UserFactory()
        room = RoomFactory(created_by=user)

        client.force_login(user)
        response = client.post(
            reverse("chat:send_message", args=[room.pk]),
            {"content": "안녕하세요"},
        )

        assert response.status_code == 302
        assert Message.objects.filter(room=room, content="안녕하세요").exists()

    def test_send_empty_message(self, client):
        """빈 메시지 전송 테스트."""
        user = UserFactory()
        room = RoomFactory(created_by=user)

        client.force_login(user)
        response = client.post(
            reverse("chat:send_message", args=[room.pk]),
            {"content": ""},
        )

        # 빈 메시지는 저장되지 않고 리다이렉트
        assert response.status_code == 302
        assert Message.objects.filter(room=room).count() == 0

    def test_non_participant_denied(self, client):
        """비참여자 전송 차단 테스트."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=other_user)

        client.force_login(user)
        response = client.post(
            reverse("chat:send_message", args=[room.pk]),
            {"content": "test"},
        )

        assert response.status_code == 403

    def test_get_method_not_allowed(self, client):
        """GET 요청 차단 테스트."""
        user = UserFactory()
        room = RoomFactory(created_by=user)

        client.force_login(user)
        response = client.get(reverse("chat:send_message", args=[room.pk]))

        assert response.status_code == 405


@pytest.mark.django_db
class TestNewConversationView:
    """새 대화 시작 뷰 테스트."""

    def test_requires_login(self, client):
        """로그인 필수 테스트."""
        url = reverse("chat:new_conversation")
        response = client.get(url)

        assert response.status_code == 302
        assert "login" in response.url

    def test_search_users(self, client):
        """사용자 검색 테스트."""
        user = UserFactory(name="테스터")
        target_user = UserFactory(name="김철수")
        UserFactory(name="홍길동")

        client.force_login(user)
        response = client.get(reverse("chat:new_conversation"), {"q": "김철수"})

        assert response.status_code == 200
        assert target_user in response.context["users"]

    def test_search_excludes_self(self, client):
        """자기 자신 검색 제외 테스트."""
        user = UserFactory(name="김철수")
        UserFactory(name="김철수2")

        client.force_login(user)
        response = client.get(reverse("chat:new_conversation"), {"q": "김철수"})

        assert user not in response.context["users"]

    def test_search_by_email(self, client):
        """이메일 검색 테스트."""
        user = UserFactory()
        target_user = UserFactory(email="target@example.com")

        client.force_login(user)
        response = client.get(reverse("chat:new_conversation"), {"q": "target"})

        assert target_user in response.context["users"]

    def test_start_new_conversation(self, client):
        """새 대화 시작 테스트."""
        user = UserFactory()
        other_user = UserFactory()

        client.force_login(user)
        response = client.post(
            reverse("chat:new_conversation"),
            {"user_id": other_user.pk},
        )

        assert response.status_code == 302
        assert (
            Room.objects.filter(
                is_direct=True,
                participants=user,
            )
            .filter(participants=other_user)
            .exists()
        )

    def test_start_existing_conversation(self, client):
        """기존 대화 조회 테스트."""
        user = UserFactory()
        other_user = UserFactory()
        existing_room = RoomFactory(created_by=user, participants=[other_user])

        client.force_login(user)
        response = client.post(
            reverse("chat:new_conversation"),
            {"user_id": other_user.pk},
        )

        assert response.status_code == 302
        assert f"/chat/{existing_room.pk}/" in response.url
        # 새로운 방이 생성되지 않음
        assert Room.objects.filter(is_direct=True).count() == 1
