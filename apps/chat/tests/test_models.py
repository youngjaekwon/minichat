"""
Chat 모델 테스트
"""

from concurrent.futures import ThreadPoolExecutor

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection

import pytest

from apps.chat.models import Message, MessageRead, Room
from tests.factories import MessageFactory, MessageReadFactory, RoomFactory, UserFactory


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


@pytest.mark.django_db
class TestMessageQuerySetSearch:
    """MessageQuerySet.search() 테스트."""

    def test_search_returns_matching_messages(self):
        """검색어가 포함된 메시지만 반환한다."""
        room = RoomFactory()
        msg1 = MessageFactory(room=room, content="안녕하세요 반갑습니다")
        msg2 = MessageFactory(room=room, content="오늘 날씨가 좋네요")
        MessageFactory(room=room, content="다른 내용")

        results = Message.objects.get_queryset().for_room(room).search("안녕")

        assert results.count() == 1
        assert msg1 in results
        assert msg2 not in results

    def test_search_case_insensitive(self):
        """대소문자 구분 없이 검색한다."""
        room = RoomFactory()
        msg = MessageFactory(room=room, content="Hello World")

        results = Message.objects.get_queryset().for_room(room).search("hello")

        assert results.count() == 1
        assert msg in results

    def test_search_partial_match(self):
        """부분 일치 검색을 지원한다."""
        room = RoomFactory()
        msg = MessageFactory(room=room, content="프로그래밍 공부하기")

        results = Message.objects.get_queryset().for_room(room).search("프로그래")

        assert results.count() == 1
        assert msg in results

    def test_search_no_results(self):
        """검색 결과가 없으면 빈 QuerySet을 반환한다."""
        room = RoomFactory()
        MessageFactory(room=room, content="안녕하세요")

        results = Message.objects.get_queryset().for_room(room).search("없는키워드")

        assert results.count() == 0

    def test_search_multiple_matches(self):
        """여러 메시지가 검색될 수 있다."""
        room = RoomFactory()
        msg1 = MessageFactory(room=room, content="오늘 회의 있어요")
        msg2 = MessageFactory(room=room, content="회의 자료 준비했습니다")
        msg3 = MessageFactory(room=room, content="회의실 예약 완료")

        results = Message.objects.get_queryset().for_room(room).search("회의")

        assert results.count() == 3
        assert msg1 in results
        assert msg2 in results
        assert msg3 in results

    def test_search_scoped_to_room(self):
        """검색은 해당 대화방 내에서만 수행된다."""
        room1 = RoomFactory()
        room2 = RoomFactory()
        msg1 = MessageFactory(room=room1, content="테스트 메시지")
        MessageFactory(room=room2, content="테스트 메시지")  # 다른 방

        results = Message.objects.get_queryset().for_room(room1).search("테스트")

        assert results.count() == 1
        assert msg1 in results


@pytest.mark.django_db
class TestMessageReadModel:
    """MessageRead 모델 테스트."""

    def test_create_message_read(self):
        """MessageRead 생성 테스트."""
        room = RoomFactory()
        user = UserFactory()
        room.participants.add(user)
        message = MessageFactory(room=room, sender=room.created_by)

        message_read = MessageReadFactory(message=message, user=user)

        assert message_read.message == message
        assert message_read.user == user
        assert message_read.read_at is not None

    def test_unique_constraint(self):
        """같은 메시지를 같은 사용자가 두 번 읽을 수 없다."""
        room = RoomFactory()
        user = UserFactory()
        room.participants.add(user)
        message = MessageFactory(room=room, sender=room.created_by)

        MessageReadFactory(message=message, user=user)

        with pytest.raises(IntegrityError):
            MessageReadFactory(message=message, user=user)

    def test_str_representation(self):
        """__str__ 메서드 테스트."""
        room = RoomFactory()
        user = UserFactory(name="테스트유저")
        room.participants.add(user)
        message = MessageFactory(room=room, sender=room.created_by)

        message_read = MessageReadFactory(message=message, user=user)

        assert str(user) in str(message_read)


@pytest.mark.django_db
class TestMessageReadManager:
    """MessageReadManager 테스트."""

    def test_mark_as_read_creates_records(self):
        """안읽은 메시지를 읽음 처리한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        # user1이 보낸 메시지 3개
        msg1 = MessageFactory(room=room, sender=user1, content="메시지1")
        msg2 = MessageFactory(room=room, sender=user1, content="메시지2")
        msg3 = MessageFactory(room=room, sender=user1, content="메시지3")

        # user2가 읽음 처리
        message_ids, sender_ids = MessageRead.objects.mark_as_read(room, user2)

        assert len(message_ids) == 3
        assert msg1.pk in message_ids
        assert msg2.pk in message_ids
        assert msg3.pk in message_ids
        assert user1.pk in sender_ids

        # MessageRead 레코드 확인
        assert MessageRead.objects.filter(user=user2).count() == 3

    def test_mark_as_read_excludes_own_messages(self):
        """자신이 보낸 메시지는 읽음 처리하지 않는다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        # user1이 보낸 메시지
        MessageFactory(room=room, sender=user1, content="user1 메시지")
        # user2가 보낸 메시지
        MessageFactory(room=room, sender=user2, content="user2 메시지")

        # user2가 읽음 처리 (자신의 메시지는 제외)
        message_ids, _ = MessageRead.objects.mark_as_read(room, user2)

        assert len(message_ids) == 1
        assert MessageRead.objects.filter(user=user2).count() == 1

    def test_mark_as_read_excludes_already_read(self):
        """이미 읽은 메시지는 다시 처리하지 않는다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        msg1 = MessageFactory(room=room, sender=user1, content="메시지1")
        MessageFactory(room=room, sender=user1, content="메시지2")

        # msg1만 미리 읽음 처리
        MessageReadFactory(message=msg1, user=user2)

        # user2가 읽음 처리
        message_ids, _ = MessageRead.objects.mark_as_read(room, user2)

        # 새로 읽음 처리된 것은 1개
        assert len(message_ids) == 1
        # 총 읽음 기록은 2개
        assert MessageRead.objects.filter(user=user2).count() == 2

    def test_mark_as_read_no_unread_messages(self):
        """안읽은 메시지가 없으면 빈 리스트를 반환한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        message_ids, sender_ids = MessageRead.objects.mark_as_read(room, user2)

        assert message_ids == []
        assert sender_ids == []

    def test_get_unread_count(self):
        """안읽은 메시지 수를 반환한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        # user1이 보낸 메시지 3개
        MessageFactory(room=room, sender=user1, content="메시지1")
        MessageFactory(room=room, sender=user1, content="메시지2")
        MessageFactory(room=room, sender=user1, content="메시지3")

        count = MessageRead.objects.get_unread_count(room, user2)

        assert count == 3

    def test_get_unread_count_excludes_own_messages(self):
        """자신이 보낸 메시지는 안읽은 수에 포함되지 않는다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        # user1이 보낸 메시지 2개
        MessageFactory(room=room, sender=user1, content="user1 메시지1")
        MessageFactory(room=room, sender=user1, content="user1 메시지2")
        # user2가 보낸 메시지 1개
        MessageFactory(room=room, sender=user2, content="user2 메시지")

        # user2 기준 안읽은 수 (자신의 메시지 제외)
        count = MessageRead.objects.get_unread_count(room, user2)

        assert count == 2

    def test_get_unread_count_excludes_read_messages(self):
        """읽은 메시지는 안읽은 수에 포함되지 않는다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        msg1 = MessageFactory(room=room, sender=user1, content="메시지1")
        MessageFactory(room=room, sender=user1, content="메시지2")

        # msg1만 읽음 처리
        MessageReadFactory(message=msg1, user=user2)

        count = MessageRead.objects.get_unread_count(room, user2)

        assert count == 1

    def test_get_unread_counts_for_rooms(self):
        """여러 채팅방의 안읽은 메시지 수를 한 번에 조회한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()

        room1 = RoomFactory(created_by=user1, participants=[user2])
        room2 = RoomFactory(created_by=user1, participants=[user2, user3])

        # room1: user1이 보낸 메시지 2개
        MessageFactory(room=room1, sender=user1, content="room1 메시지1")
        MessageFactory(room=room1, sender=user1, content="room1 메시지2")

        # room2: user1이 보낸 메시지 3개
        msg = MessageFactory(room=room2, sender=user1, content="room2 메시지1")
        MessageFactory(room=room2, sender=user1, content="room2 메시지2")
        MessageFactory(room=room2, sender=user1, content="room2 메시지3")

        # user2가 참여한 방만 조회 (실제 사용 패턴)
        rooms_user2 = Room.objects.get_by_user(user2)
        counts_user2 = MessageRead.objects.get_unread_counts_for_rooms(rooms_user2, user2)

        assert counts_user2.get(room1.pk, 0) == 2
        assert counts_user2.get(room2.pk, 0) == 3

        # user2가 room2의 메시지 1개를 읽음
        MessageReadFactory(message=msg, user=user2)

        counts_user2 = MessageRead.objects.get_unread_counts_for_rooms(rooms_user2, user2)
        assert counts_user2.get(room2.pk, 0) == 2  # 3 - 1 = 2

        # user3 기준 (room2만 참여)
        rooms_user3 = Room.objects.get_by_user(user3)
        counts_user3 = MessageRead.objects.get_unread_counts_for_rooms(rooms_user3, user3)

        assert counts_user3.get(room1.pk, 0) == 0  # room1에 참여 안 함
        assert counts_user3.get(room2.pk, 0) == 3


@pytest.mark.django_db
class TestMessageQuerySetWithUnreadCount:
    """MessageQuerySet.with_unread_count() 테스트."""

    def test_with_unread_count_new_message(self):
        """새 메시지의 unread_count는 참여자수 - 1 (발신자 제외)."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        message = MessageFactory(room=room, sender=user1, content="테스트")

        messages = list(Message.objects.filter(pk=message.pk).with_unread_count())

        assert len(messages) == 1
        # 참여자 2명, 읽은 사람 0명, 발신자 제외 = 2 - 0 - 1 = 1
        assert messages[0].unread_count == 1

    def test_with_unread_count_after_read(self):
        """읽음 처리 후 unread_count가 감소한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        message = MessageFactory(room=room, sender=user1, content="테스트")

        # user2가 읽음 처리
        MessageReadFactory(message=message, user=user2)

        messages = list(Message.objects.filter(pk=message.pk).with_unread_count())

        assert len(messages) == 1
        # 참여자 2명, 읽은 사람 1명, 발신자 제외 = 2 - 1 - 1 = 0
        assert messages[0].unread_count == 0

    def test_with_unread_count_group_chat(self):
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

        messages = list(Message.objects.filter(pk=message.pk).with_unread_count())

        # 참여자 3명, 읽은 사람 0명, 발신자 제외 = 3 - 0 - 1 = 2
        assert messages[0].unread_count == 2

        # user2가 읽음
        MessageReadFactory(message=message, user=user2)

        messages = list(Message.objects.filter(pk=message.pk).with_unread_count())

        # 참여자 3명, 읽은 사람 1명, 발신자 제외 = 3 - 1 - 1 = 1
        assert messages[0].unread_count == 1

        # user3도 읽음
        MessageReadFactory(message=message, user=user3)

        messages = list(Message.objects.filter(pk=message.pk).with_unread_count())

        # 참여자 3명, 읽은 사람 2명, 발신자 제외 = 3 - 2 - 1 = 0
        assert messages[0].unread_count == 0

    def test_with_unread_count_multiple_messages(self):
        """여러 메시지의 unread_count를 한 번에 조회한다."""
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory(created_by=user1, participants=[user2])

        msg1 = MessageFactory(room=room, sender=user1, content="메시지1")
        msg2 = MessageFactory(room=room, sender=user1, content="메시지2")
        msg3 = MessageFactory(room=room, sender=user1, content="메시지3")

        # msg1만 읽음 처리
        MessageReadFactory(message=msg1, user=user2)

        messages = list(
            Message.objects.filter(pk__in=[msg1.pk, msg2.pk, msg3.pk])
            .with_unread_count()
            .order_by("pk")
        )

        assert messages[0].unread_count == 0  # msg1: 읽음
        assert messages[1].unread_count == 1  # msg2: 안읽음
        assert messages[2].unread_count == 1  # msg3: 안읽음
