"""
Chat API 테스트
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import MessageFactory, RoomFactory, UserFactory


@pytest.fixture
def api_client():
    """API 클라이언트 픽스처."""
    return APIClient()


@pytest.mark.django_db
class TestMessageSearchAPI:
    """MessageSearchAPIView 테스트."""

    def test_search_returns_message_ids(self, api_client):
        """검색 결과로 메시지 ID 목록을 반환한다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        msg1 = MessageFactory(room=room, sender=user, content="안녕하세요")
        msg2 = MessageFactory(room=room, sender=user, content="안녕히 가세요")
        MessageFactory(room=room, sender=user, content="다른 내용")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url, {"q": "안녕"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total"] == 2
        assert msg1.pk in response.data["message_ids"]
        assert msg2.pk in response.data["message_ids"]

    def test_search_returns_chronological_order(self, api_client):
        """검색 결과는 시간순으로 정렬된다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        msg1 = MessageFactory(room=room, sender=user, content="테스트 첫번째")
        msg2 = MessageFactory(room=room, sender=user, content="테스트 두번째")
        msg3 = MessageFactory(room=room, sender=user, content="테스트 세번째")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message_ids"] == [msg1.pk, msg2.pk, msg3.pk]

    def test_search_no_results(self, api_client):
        """검색 결과가 없으면 빈 목록을 반환한다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])
        MessageFactory(room=room, sender=user, content="안녕하세요")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url, {"q": "없는키워드"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total"] == 0
        assert response.data["message_ids"] == []

    def test_search_requires_min_length(self, api_client):
        """검색어는 최소 2자 이상이어야 한다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url, {"q": "가"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_requires_query_param(self, api_client):
        """검색어 파라미터가 필수이다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_requires_authentication(self, api_client):
        """인증이 필요하다.

        SessionAuthentication 사용 시 403 반환 (401은 WWW-Authenticate 헤더 필요).
        """
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_requires_room_participant(self, api_client):
        """대화방 참여자만 검색할 수 있다."""
        user1 = UserFactory()
        user2 = UserFactory()
        outsider = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])
        MessageFactory(room=room, sender=user1, content="테스트 메시지")

        api_client.force_authenticate(user=outsider)
        url = reverse("chat:api_messages_search", kwargs={"room_id": room.pk})
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_room_not_found(self, api_client):
        """존재하지 않는 대화방은 403을 반환한다.

        보안상 room 존재 여부를 노출하지 않기 위해 403 반환.
        """
        user = UserFactory()

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_messages_search", kwargs={"room_id": 99999})
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
