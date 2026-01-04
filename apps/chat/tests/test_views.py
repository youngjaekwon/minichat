"""
Chat 뷰 테스트
"""

from django.urls import reverse

import pytest

from apps.chat.models import Room
from tests.factories import MessageFactory, MessageReadFactory, RoomFactory, UserFactory


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

    def test_includes_unread_counts(self, client):
        """안읽은 메시지 수가 컨텍스트에 포함된다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=other_user, participants=[user])

        # other_user가 보낸 메시지 3개
        MessageFactory(room=room, sender=other_user, content="메시지1")
        MessageFactory(room=room, sender=other_user, content="메시지2")
        MessageFactory(room=room, sender=other_user, content="메시지3")

        client.force_login(user)
        response = client.get(reverse("chat:room_list"))

        assert response.status_code == 200
        assert "unread_counts" in response.context
        assert response.context["unread_counts"].get(room.pk, 0) == 3

    def test_unread_counts_excludes_own_messages(self, client):
        """자신이 보낸 메시지는 안읽은 수에 포함되지 않는다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        # user가 보낸 메시지
        MessageFactory(room=room, sender=user, content="내 메시지")
        # other_user가 보낸 메시지
        MessageFactory(room=room, sender=other_user, content="상대방 메시지")

        client.force_login(user)
        response = client.get(reverse("chat:room_list"))

        # user 기준 안읽은 수는 1 (상대방 메시지만)
        assert response.context["unread_counts"].get(room.pk, 0) == 1

    def test_unread_counts_excludes_read_messages(self, client):
        """읽은 메시지는 안읽은 수에 포함되지 않는다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=other_user, participants=[user])

        msg1 = MessageFactory(room=room, sender=other_user, content="메시지1")
        MessageFactory(room=room, sender=other_user, content="메시지2")

        # msg1만 읽음 처리
        MessageReadFactory(message=msg1, user=user)

        client.force_login(user)
        response = client.get(reverse("chat:room_list"))

        # 1개 읽음, 1개 안읽음
        assert response.context["unread_counts"].get(room.pk, 0) == 1


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

    def test_shows_room_detail(self, client):
        """대화방 상세 페이지 로드 테스트.

        메시지는 API를 통해 로드되므로 페이지 로드 성공만 확인.
        """
        user = UserFactory()
        room = RoomFactory(created_by=user)
        MessageFactory(room=room, sender=user, content="테스트 메시지")

        client.force_login(user)
        response = client.get(reverse("chat:room_detail", args=[room.pk]))

        assert response.status_code == 200
        assert response.context["selected_room"] == room

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

    def test_includes_participant_count(self, client):
        """참여자 수가 컨텍스트에 포함된다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        client.force_login(user)
        response = client.get(reverse("chat:room_detail", args=[room.pk]))

        assert response.context["participant_count"] == 2

    def test_includes_unread_counts(self, client):
        """채팅방 목록의 안읽은 메시지 수가 컨텍스트에 포함된다."""
        user = UserFactory()
        other_user = UserFactory()
        third_user = UserFactory()

        room1 = RoomFactory(created_by=other_user, participants=[user])
        room2 = RoomFactory(created_by=third_user, participants=[user])

        # room1: other_user가 보낸 메시지 2개
        MessageFactory(room=room1, sender=other_user, content="room1 메시지1")
        MessageFactory(room=room1, sender=other_user, content="room1 메시지2")

        # room2: third_user가 보낸 메시지 1개
        MessageFactory(room=room2, sender=third_user, content="room2 메시지1")

        client.force_login(user)
        response = client.get(reverse("chat:room_detail", args=[room1.pk]))

        assert "unread_counts" in response.context
        assert response.context["unread_counts"].get(room1.pk, 0) == 2
        assert response.context["unread_counts"].get(room2.pk, 0) == 1


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
