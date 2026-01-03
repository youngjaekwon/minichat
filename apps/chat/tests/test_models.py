"""
Chat 모델 테스트
"""

from concurrent.futures import ThreadPoolExecutor

from django.core.exceptions import ValidationError
from django.db import connection

import pytest

from apps.chat.models import Message, Room
from tests.factories import MessageFactory, RoomFactory, UserFactory


@pytest.mark.django_db
class TestRoomModel:
    """Room 모델 테스트."""

    def test_create_direct_room(self):
        """1:1 대화방 생성 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        assert room.is_direct is True
        assert room.name == ""
        assert room.created_by == user1
        assert room.participants.count() == 2
        assert user1 in room.participants.all()
        assert user2 in room.participants.all()

    def test_create_group_room(self):
        """그룹 대화방 생성 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        room = RoomFactory(
            name="테스트 그룹",
            is_direct=False,
            created_by=user1,
            participants=[user2, user3],
        )

        assert room.is_direct is False
        assert room.name == "테스트 그룹"
        assert room.participants.count() == 3

    def test_add_participant(self):
        """참여자 추가 테스트."""
        room = RoomFactory()
        new_user = UserFactory()

        room.participants.add(new_user)

        assert new_user in room.participants.all()

    def test_get_display_name_direct(self):
        """1:1 대화방 표시 이름 테스트."""
        user1 = UserFactory(name="홍길동")
        user2 = UserFactory(name="김철수")
        room = RoomFactory(created_by=user1, participants=[user2])

        assert room.get_display_name(user1) == "김철수"
        assert room.get_display_name(user2) == "홍길동"

    def test_get_display_name_group(self):
        """그룹 대화방 표시 이름 테스트."""
        user1 = UserFactory()
        room = RoomFactory(name="테스트 그룹", is_direct=False, created_by=user1)

        assert room.get_display_name(user1) == "테스트 그룹"

    def test_get_other_participant(self):
        """상대방 조회 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        assert room.get_other_participant(user1) == user2
        assert room.get_other_participant(user2) == user1

    def test_get_other_participant_group(self):
        """그룹 대화방에서 상대방 조회 시 None 반환."""
        user1 = UserFactory()
        room = RoomFactory(is_direct=False, created_by=user1)

        assert room.get_other_participant(user1) is None

    def test_is_participant(self):
        """참여자 확인 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        assert room.is_participant(user1) is True
        assert room.is_participant(user2) is True
        assert room.is_participant(user3) is False

    def test_get_last_message(self):
        """마지막 메시지 조회 테스트."""
        room = RoomFactory()
        user = room.created_by

        MessageFactory(room=room, sender=user, content="첫 번째 메시지")
        msg2 = MessageFactory(room=room, sender=user, content="두 번째 메시지")

        assert room.get_last_message() == msg2

    def test_get_last_message_empty(self):
        """메시지 없을 때 None 반환."""
        room = RoomFactory()

        assert room.get_last_message() is None


@pytest.mark.django_db
class TestMessageModel:
    """Message 모델 테스트."""

    def test_create_message(self):
        """메시지 생성 테스트."""
        room = RoomFactory()
        user = room.created_by
        message = MessageFactory(room=room, sender=user, content="안녕하세요")

        assert message.room == room
        assert message.sender == user
        assert message.content == "안녕하세요"
        assert message.created_at is not None

    def test_empty_message_validation(self):
        """빈 메시지 검증 테스트."""
        room = RoomFactory()
        user = room.created_by
        message = Message(room=room, sender=user, content="")

        with pytest.raises(ValidationError) as exc_info:
            message.full_clean()

        assert "content" in exc_info.value.message_dict

    def test_whitespace_message_validation(self):
        """공백만 있는 메시지 검증 테스트."""
        room = RoomFactory()
        user = room.created_by
        message = Message(room=room, sender=user, content="   ")

        with pytest.raises(ValidationError):
            message.full_clean()

    def test_get_preview(self):
        """메시지 미리보기 테스트."""
        room = RoomFactory()
        short_message = MessageFactory(room=room, content="짧은 메시지")
        long_content = "가" * 60  # 60자 메시지
        long_message = MessageFactory(room=room, content=long_content)

        assert short_message.get_preview() == "짧은 메시지"
        assert len(long_message.get_preview()) == 53  # 50자 + "..."
        assert long_message.get_preview().endswith("...")


@pytest.mark.django_db
class TestRoomManager:
    """RoomManager 테스트."""

    def test_get_by_user(self):
        """사용자별 대화방 조회 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()

        room1 = RoomFactory(created_by=user1, participants=[user2])
        room2 = RoomFactory(created_by=user1, participants=[user3])
        RoomFactory(created_by=user2, participants=[user3])  # user1이 없는 방

        rooms = Room.objects.get_by_user(user1)

        assert rooms.count() == 2
        assert room1 in rooms
        assert room2 in rooms

    def test_get_by_user_ordered(self):
        """대화방 정렬 테스트 (최근 업데이트 순)."""
        user = UserFactory()
        other_user1 = UserFactory()
        other_user2 = UserFactory()

        room1 = RoomFactory(created_by=user, participants=[other_user1])
        room2 = RoomFactory(created_by=user, participants=[other_user2])

        # room1에 메시지 추가 (create_message가 room.save()를 호출하여 updated_at 갱신)
        Message.objects.create_message(room=room1, sender=user, content="테스트")

        rooms = list(Room.objects.get_by_user(user))

        # room1이 더 최근에 업데이트되었으므로 먼저
        assert rooms[0] == room1
        assert rooms[1] == room2

    def test_get_or_create_direct_existing(self):
        """기존 1:1 대화방 조회 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        existing_room = RoomFactory(created_by=user1, participants=[user2])

        room = Room.objects.get_or_create_direct(user1, user2)

        assert room == existing_room

    def test_get_or_create_direct_new(self):
        """새 1:1 대화방 생성 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()

        room = Room.objects.get_or_create_direct(user1, user2)

        assert room.is_direct is True
        assert room.created_by == user1
        assert room.participants.count() == 2

    def test_get_or_create_direct_prevents_duplicate(self):
        """중복 1:1 대화방 방지 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()

        room1 = Room.objects.get_or_create_direct(user1, user2)
        room2 = Room.objects.get_or_create_direct(user2, user1)

        assert room1 == room2

    def test_create_group(self):
        """그룹 대화방 생성 테스트."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()

        room = Room.objects.create_group(
            name="테스트 그룹",
            created_by=user1,
            participants=[user2, user3],
        )

        assert room.is_direct is False
        assert room.name == "테스트 그룹"
        assert room.created_by == user1
        assert room.participants.count() == 3
        assert user1 in room.participants.all()


@pytest.mark.django_db(transaction=True)
class TestRoomManagerConcurrency:
    """RoomManager 동시성 테스트."""

    @pytest.mark.skipif(
        connection.vendor == "sqlite",
        reason="SQLite는 동시 쓰기를 지원하지 않음",
    )
    def test_get_or_create_direct_concurrent(self):
        """동시에 1:1 대화방 생성 시도해도 중복 방지."""
        user1 = UserFactory()
        user2 = UserFactory()
        results = []

        def create_room():
            # 각 스레드에서 새 DB 연결 사용
            connection.close()
            room = Room.objects.get_or_create_direct(user1, user2)
            results.append(room.pk)

        # 10개의 스레드에서 동시에 대화방 생성 시도
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_room) for _ in range(10)]
            for future in futures:
                future.result()

        # 모두 같은 Room ID를 받아야 함
        assert len(set(results)) == 1
        # DB에 1:1 대화방은 하나만 존재해야 함
        assert Room.objects.filter(is_direct=True).count() == 1


@pytest.mark.django_db
class TestMessageManager:
    """MessageManager 테스트."""

    def test_get_by_room(self):
        """대화방별 메시지 조회 테스트."""
        room1 = RoomFactory()
        room2 = RoomFactory()

        msg1 = MessageFactory(room=room1, content="메시지 1")
        msg2 = MessageFactory(room=room1, content="메시지 2")
        MessageFactory(room=room2, content="다른 방 메시지")

        messages = Message.objects.get_by_room(room1)

        assert messages.count() == 2
        assert msg1 in messages
        assert msg2 in messages

    def test_get_by_room_ordered(self):
        """메시지 정렬 테스트 (시간 오름차순)."""
        room = RoomFactory()
        msg1 = MessageFactory(room=room, content="첫 번째")
        msg2 = MessageFactory(room=room, content="두 번째")

        messages = list(Message.objects.get_by_room(room))

        assert messages[0] == msg1
        assert messages[1] == msg2

    def test_create_message(self):
        """메시지 생성 테스트."""
        room = RoomFactory()
        user = room.created_by
        old_updated_at = room.updated_at

        message = Message.objects.create_message(
            room=room,
            sender=user,
            content="테스트 메시지",
        )

        room.refresh_from_db()

        assert message.content == "테스트 메시지"
        assert message.sender == user
        assert room.updated_at > old_updated_at

    def test_create_message_empty_fails(self):
        """빈 메시지 생성 실패 테스트."""
        room = RoomFactory()
        user = room.created_by

        with pytest.raises(ValidationError):
            Message.objects.create_message(
                room=room,
                sender=user,
                content="",
            )
