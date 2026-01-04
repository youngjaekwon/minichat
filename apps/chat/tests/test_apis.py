"""
Chat API 테스트
"""

from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import MessageFactory, MessageReadFactory, RoomFactory, UserFactory


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


@pytest.mark.django_db
class TestMessageListAPI:
    """MessageListAPIView 테스트."""

    def test_messages_include_unread_count(self, api_client):
        """메시지 목록에 unread_count 필드가 포함된다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        MessageFactory(room=room, sender=user1, content="테스트")

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["messages"]) == 1
        assert "unread_count" in response.data["messages"][0]

    def test_unread_count_for_new_message(self, api_client):
        """새 메시지의 unread_count는 참여자수 - 1 (발신자 제외)."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        MessageFactory(room=room, sender=user1, content="테스트")

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # 참여자 2명, 읽은 사람 0명, 발신자 제외 = 2 - 0 - 1 = 1
        assert response.data["messages"][0]["unread_count"] == 1

    def test_unread_count_decreases_after_read(self, api_client):
        """읽음 처리 후 unread_count가 감소한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        message = MessageFactory(room=room, sender=user1, content="테스트")

        # user2가 메시지 읽음
        MessageReadFactory(message=message, user=user2)

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # 참여자 2명, 읽은 사람 1명, 발신자 제외 = 2 - 1 - 1 = 0
        assert response.data["messages"][0]["unread_count"] == 0

    def test_unread_count_in_group_chat(self, api_client):
        """그룹 채팅에서 unread_count 계산."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        room = RoomFactory(
            name="그룹",
            is_direct=False,
            created_by=user1,
            participants=[user2, user3],
        )

        message = MessageFactory(room=room, sender=user1, content="테스트")

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        # 참여자 3명, 읽은 사람 0명, 발신자 제외 = 3 - 0 - 1 = 2
        assert response.data["messages"][0]["unread_count"] == 2

        # user2가 읽음
        MessageReadFactory(message=message, user=user2)

        response = api_client.get(url)

        # 참여자 3명, 읽은 사람 1명, 발신자 제외 = 3 - 1 - 1 = 1
        assert response.data["messages"][0]["unread_count"] == 1

    def test_multiple_messages_with_different_unread_counts(self, api_client):
        """여러 메시지의 unread_count가 각각 올바르게 계산된다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        msg1 = MessageFactory(room=room, sender=user1, content="메시지1")
        msg2 = MessageFactory(room=room, sender=user1, content="메시지2")
        MessageFactory(room=room, sender=user1, content="메시지3")

        # msg1만 읽음 처리
        MessageReadFactory(message=msg1, user=user2)

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        messages = response.data["messages"]

        # 시간순 정렬 (오래된 것 먼저)
        msg1_data = next(m for m in messages if m["id"] == msg1.pk)
        msg2_data = next(m for m in messages if m["id"] == msg2.pk)

        assert msg1_data["unread_count"] == 0  # 읽음
        assert msg2_data["unread_count"] == 1  # 안읽음

    def test_requires_authentication(self, api_client):
        """인증이 필요하다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_requires_room_participant(self, api_client):
        """대화방 참여자만 조회할 수 있다."""
        user1 = UserFactory()
        user2 = UserFactory()
        outsider = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        api_client.force_authenticate(user=outsider)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pagination_cursors(self, api_client):
        """cursor 기반 페이지네이션이 동작한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        # 메시지 5개 생성
        messages = []
        for i in range(5):
            messages.append(
                MessageFactory(room=room, sender=user1, content=f"메시지{i}")
            )

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})

        # 기본 조회 (최신 메시지부터)
        response = api_client.get(url, {"limit": 3})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["messages"]) == 3
        assert response.data["has_more_before"] is True
        assert response.data["has_more_after"] is False

    def test_direction_before(self, api_client):
        """direction=before로 이전 메시지를 조회한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        # 메시지 5개 생성
        messages = []
        for i in range(5):
            messages.append(
                MessageFactory(room=room, sender=user1, content=f"메시지{i}")
            )

        api_client.force_authenticate(user=user1)
        url = reverse("chat:api_messages", kwargs={"room_id": room.pk})

        # 마지막 메시지 이전 조회
        response = api_client.get(url, {
            "direction": "before",
            "cursor": messages[4].pk,
            "limit": 2,
        })

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["messages"]) == 2
        # 시간순 정렬 (오래된 것 먼저)
        assert response.data["messages"][0]["id"] == messages[2].pk
        assert response.data["messages"][1]["id"] == messages[3].pk


@pytest.mark.django_db
class TestRoomSearchAPI:
    """RoomSearchAPIView 테스트."""

    def test_search_returns_rooms_with_matching_messages(self, api_client):
        """메시지 내용이 일치하는 대화방 목록을 반환한다."""
        user = UserFactory()
        other_user1 = UserFactory()
        other_user2 = UserFactory()

        room1 = RoomFactory(created_by=user, participants=[other_user1])
        room2 = RoomFactory(created_by=user, participants=[other_user2])

        MessageFactory(room=room1, sender=user, content="안녕하세요 테스트입니다")
        MessageFactory(room=room2, sender=user, content="다른 내용")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 1
        assert response.data["rooms"][0]["id"] == room1.pk

    def test_search_returns_matched_message_preview(self, api_client):
        """검색 결과에 일치하는 메시지 미리보기가 포함된다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        MessageFactory(room=room, sender=user, content="검색 키워드가 있는 메시지")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "키워드"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 1
        assert "키워드" in response.data["rooms"][0]["matched_message_preview"]

    def test_search_returns_display_name(self, api_client):
        """검색 결과에 대화방 표시 이름이 포함된다."""
        user = UserFactory()
        other_user = UserFactory(name="상대방")
        room = RoomFactory(created_by=user, participants=[other_user])

        MessageFactory(room=room, sender=user, content="검색 테스트")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["rooms"][0]["display_name"] == "상대방"

    def test_search_no_results(self, api_client):
        """검색 결과가 없으면 빈 목록을 반환한다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])
        MessageFactory(room=room, sender=user, content="안녕하세요")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "없는키워드"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["rooms"] == []

    def test_search_requires_min_length(self, api_client):
        """검색어는 최소 2자 이상이어야 한다."""
        user = UserFactory()

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "가"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_requires_query_param(self, api_client):
        """검색어 파라미터가 필수이다."""
        user = UserFactory()

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_requires_authentication(self, api_client):
        """인증이 필요하다."""
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_only_returns_participating_rooms(self, api_client):
        """사용자가 참여 중인 대화방에서만 검색한다."""
        user = UserFactory()
        other_user1 = UserFactory()
        other_user2 = UserFactory()

        # user가 참여 중인 대화방
        room1 = RoomFactory(created_by=user, participants=[other_user1])
        MessageFactory(room=room1, sender=user, content="검색 테스트")

        # user가 참여하지 않는 대화방
        room2 = RoomFactory(created_by=other_user1, participants=[other_user2])
        MessageFactory(room=room2, sender=other_user1, content="검색 테스트")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "테스트"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 1
        assert response.data["rooms"][0]["id"] == room1.pk

    def test_search_is_case_insensitive(self, api_client):
        """대소문자 구분 없이 검색한다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        MessageFactory(room=room, sender=user, content="Hello World")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "hello"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 1


@pytest.mark.django_db
class TestRoomListAPIPagination:
    """RoomListAPIView 페이지네이션 테스트."""

    def test_returns_paginated_rooms(self, api_client):
        """페이지네이션된 대화방 목록을 반환한다."""
        user = UserFactory()

        # 5개의 대화방 생성
        for _ in range(5):
            other_user = UserFactory()
            RoomFactory(created_by=user, participants=[other_user])

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")
        response = api_client.get(url, {"limit": 3})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 3
        assert response.data["has_more"] is True
        assert response.data["next_cursor"] is not None

    def test_load_more_with_cursor(self, api_client):
        """커서로 다음 페이지를 로드한다."""
        user = UserFactory()

        # 5개의 대화방 생성
        for _ in range(5):
            other_user = UserFactory()
            RoomFactory(created_by=user, participants=[other_user])

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")

        # 첫 번째 페이지 로드
        response1 = api_client.get(url, {"limit": 3})
        assert response1.status_code == status.HTTP_200_OK
        first_page_ids = [r["id"] for r in response1.data["rooms"]]

        # 두 번째 페이지 로드
        response2 = api_client.get(
            url,
            {"cursor": response1.data["next_cursor"], "limit": 3},
        )
        assert response2.status_code == status.HTTP_200_OK
        second_page_ids = [r["id"] for r in response2.data["rooms"]]

        # 중복 없이 다른 대화방이 반환되어야 함
        assert len(set(first_page_ids) & set(second_page_ids)) == 0

    def test_has_more_false_when_no_more_data(self, api_client):
        """더 이상 데이터가 없으면 has_more가 False다."""
        user = UserFactory()
        other_user = UserFactory()
        RoomFactory(created_by=user, participants=[other_user])

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")
        response = api_client.get(url, {"limit": 10})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_more"] is False
        assert response.data["next_cursor"] is None

    def test_returns_rooms_without_cursor(self, api_client):
        """커서 없이 호출하면 최신 대화방부터 반환한다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 1
        assert response.data["rooms"][0]["id"] == room.pk

    def test_returns_unread_count(self, api_client):
        """대화방 목록에 안읽은 메시지 수가 포함된다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        # other_user가 보낸 메시지 3개 (user 기준 안읽음)
        MessageFactory(room=room, sender=other_user, content="메시지1")
        MessageFactory(room=room, sender=other_user, content="메시지2")
        MessageFactory(room=room, sender=other_user, content="메시지3")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 1
        assert "unread_count" in response.data["rooms"][0]
        assert response.data["rooms"][0]["unread_count"] == 3

    def test_unread_count_excludes_own_messages(self, api_client):
        """자신이 보낸 메시지는 안읽은 수에 포함되지 않는다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        # user가 보낸 메시지 (안읽은 수에 포함 안됨)
        MessageFactory(room=room, sender=user, content="내 메시지")
        # other_user가 보낸 메시지 (안읽은 수에 포함)
        MessageFactory(room=room, sender=other_user, content="상대방 메시지")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["rooms"][0]["unread_count"] == 1

    def test_unread_count_excludes_read_messages(self, api_client):
        """읽은 메시지는 안읽은 수에 포함되지 않는다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])

        msg1 = MessageFactory(room=room, sender=other_user, content="메시지1")
        MessageFactory(room=room, sender=other_user, content="메시지2")

        # msg1만 읽음 처리
        MessageReadFactory(message=msg1, user=user)

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # 1개 읽음, 1개 안읽음
        assert response.data["rooms"][0]["unread_count"] == 1


@pytest.mark.django_db
class TestRoomSearchAPIPagination:
    """RoomSearchAPIView 페이지네이션 테스트."""

    def test_returns_paginated_search_results(self, api_client):
        """페이지네이션된 검색 결과를 반환한다."""
        user = UserFactory()

        # 5개의 대화방에 검색어가 포함된 메시지 생성
        for i in range(5):
            other_user = UserFactory()
            room = RoomFactory(created_by=user, participants=[other_user])
            MessageFactory(room=room, sender=user, content=f"테스트 메시지 {i}")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "테스트", "limit": 3})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["rooms"]) == 3
        assert response.data["has_more"] is True
        assert response.data["next_cursor"] is not None

    def test_load_more_search_results_with_cursor(self, api_client):
        """커서로 다음 검색 결과 페이지를 로드한다."""
        user = UserFactory()

        # 5개의 대화방에 검색어가 포함된 메시지 생성
        for i in range(5):
            other_user = UserFactory()
            room = RoomFactory(created_by=user, participants=[other_user])
            MessageFactory(room=room, sender=user, content=f"검색어 {i}")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")

        # 첫 번째 페이지 로드
        response1 = api_client.get(url, {"q": "검색어", "limit": 3})
        assert response1.status_code == status.HTTP_200_OK
        first_page_ids = [r["id"] for r in response1.data["rooms"]]

        # 두 번째 페이지 로드
        response2 = api_client.get(
            url,
            {"q": "검색어", "cursor": response1.data["next_cursor"], "limit": 3},
        )
        assert response2.status_code == status.HTTP_200_OK
        second_page_ids = [r["id"] for r in response2.data["rooms"]]

        # 중복 없이 다른 대화방이 반환되어야 함
        assert len(set(first_page_ids) & set(second_page_ids)) == 0

    def test_search_has_more_false_when_no_more_results(self, api_client):
        """더 이상 검색 결과가 없으면 has_more가 False다."""
        user = UserFactory()
        other_user = UserFactory()
        room = RoomFactory(created_by=user, participants=[other_user])
        MessageFactory(room=room, sender=user, content="유일한 테스트")

        api_client.force_authenticate(user=user)
        url = reverse("chat:api_rooms_search")
        response = api_client.get(url, {"q": "테스트", "limit": 10})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_more"] is False
        assert response.data["next_cursor"] is None
