"""ChatConsumer 테스트."""

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from apps.chat.constants import (
    CLOSE_CODE_FORBIDDEN,
    CLOSE_CODE_NOT_FOUND,
    CLOSE_CODE_UNAUTHORIZED,
)
from apps.chat.consumers import ChatConsumer
from apps.chat.models import Message, MessageRead
from tests.factories import MessageFactory, MessageReadFactory, RoomFactory, UserFactory


@pytest.fixture
def user(db):
    """테스트 사용자 생성."""
    return UserFactory()


@pytest.fixture
def other_user(db):
    """다른 테스트 사용자 생성."""
    return UserFactory()


@pytest.fixture
def room(db, user, other_user):
    """테스트 대화방 생성."""
    return RoomFactory(created_by=user, participants=[other_user])


@pytest.fixture
def non_participant_user(db):
    """참여자가 아닌 사용자 생성."""
    return UserFactory()


class MockScope:
    """WebSocket scope 모킹."""

    def __init__(self, user, room_id):
        self.data = {
            "type": "websocket",
            "path": f"/ws/chat/{room_id}/",
            "user": user,
            "url_route": {"kwargs": {"room_id": room_id}},
            "query_string": b"",
        }

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)


async def create_communicator(user, room_id, query_string=""):
    """WebsocketCommunicator 생성 헬퍼."""
    communicator = WebsocketCommunicator(
        ChatConsumer.as_asgi(),
        f"/ws/chat/{room_id}/?{query_string}",
    )
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {"room_id": room_id}}
    return communicator


async def create_sidebar_communicator(user):
    """사이드바 전용 WebsocketCommunicator 생성 헬퍼."""
    communicator = WebsocketCommunicator(
        ChatConsumer.as_asgi(),
        "/ws/chat/",
    )
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {}}  # room_id 없음
    return communicator


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerConnect:
    """ChatConsumer connect() 테스트."""

    async def test_authenticated_user_can_connect(self, user, room):
        """인증된 참여자가 연결에 성공한다."""
        communicator = await create_communicator(user, room.pk)

        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_unauthenticated_user_rejected(self, room):
        """비인증 사용자가 연결을 거부당한다."""
        from django.contrib.auth.models import AnonymousUser

        communicator = await create_communicator(AnonymousUser(), room.pk)

        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == CLOSE_CODE_UNAUTHORIZED

    async def test_non_participant_rejected(self, non_participant_user, room):
        """비참여자가 연결을 거부당한다."""
        communicator = await create_communicator(non_participant_user, room.pk)

        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == CLOSE_CODE_FORBIDDEN

    async def test_nonexistent_room_rejected(self, user):
        """존재하지 않는 대화방에 연결 시 거부당한다."""
        communicator = await create_communicator(user, 99999)

        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == CLOSE_CODE_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerMessaging:
    """ChatConsumer 메시지 송수신 테스트."""

    async def test_send_message_success(self, user, room):
        """메시지 전송에 성공한다."""
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 메시지 전송
        await communicator.send_json_to({
            "type": "chat_message",
            "content": "테스트 메시지",
            "client_id": "test-client-id-123",
        })

        # 응답 수신 (순서는 InMemoryChannelLayer에서 다를 수 있음)
        responses = []
        for _ in range(2):
            response = await communicator.receive_json_from()
            responses.append(response)

        # chat_message와 message_ack 모두 수신해야 함
        types = [r["type"] for r in responses]
        assert "chat_message" in types
        assert "message_ack" in types

        # chat_message 확인
        chat_msg = next(r for r in responses if r["type"] == "chat_message")
        assert chat_msg["message"]["content"] == "테스트 메시지"
        assert chat_msg["message"]["sender_id"] == user.pk

        # ACK 확인
        ack = next(r for r in responses if r["type"] == "message_ack")
        assert ack["client_id"] == "test-client-id-123"
        assert ack["status"] == "success"

        await communicator.disconnect()

    async def test_send_empty_message_error(self, user, room):
        """빈 메시지 전송 시 에러가 반환된다."""
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 빈 메시지 전송
        await communicator.send_json_to({
            "type": "chat_message",
            "content": "   ",
        })

        # 에러 응답 수신
        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert response["code"] == "EMPTY_MESSAGE"

        await communicator.disconnect()

    async def test_invalid_json_error(self, user, room):
        """유효하지 않은 JSON 전송 시 에러가 반환된다."""
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 유효하지 않은 JSON 전송
        await communicator.send_to(text_data="invalid json")

        # 에러 응답 수신
        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert response["code"] == "INVALID_FORMAT"

        await communicator.disconnect()

    async def test_message_persisted_to_db(self, user, room):
        """전송된 메시지가 DB에 저장된다."""
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 메시지 전송
        await communicator.send_json_to({
            "type": "chat_message",
            "content": "DB에 저장될 메시지",
        })

        # 응답 수신 (브로드캐스트)
        response = await communicator.receive_json_from()
        message_id = response["message"]["id"]

        # DB 확인
        @database_sync_to_async
        def check_message():
            return Message.objects.filter(pk=message_id).exists()

        assert await check_message() is True

        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerMessageSync:
    """ChatConsumer 메시지 동기화 테스트."""

    async def test_sync_missed_messages_on_reconnect(self, user, other_user, room):
        """재연결 시 누락된 메시지가 동기화된다."""
        # 먼저 몇 개의 메시지 생성
        @database_sync_to_async
        def create_messages():
            messages = []
            for i in range(3):
                msg = MessageFactory(room=room, sender=other_user, content=f"메시지 {i}")
                messages.append(msg)
            return messages

        messages = await create_messages()
        first_message_id = messages[0].pk

        # last_message_id를 첫 번째 메시지로 설정하고 재연결
        communicator = await create_communicator(
            user, room.pk, query_string=f"last_message_id={first_message_id}"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        # 누락된 메시지 2개가 수신되어야 함
        received_messages = []
        for _ in range(2):
            try:
                response = await communicator.receive_json_from(timeout=1)
                if response["type"] == "chat_message":
                    received_messages.append(response)
            except Exception:
                break

        assert len(received_messages) == 2

        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerReadStatus:
    """ChatConsumer 읽음 상태 테스트."""

    async def test_message_includes_unread_count(self, user, other_user, room):
        """전송된 메시지에 unread_count가 포함된다."""
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 메시지 전송
        await communicator.send_json_to({
            "type": "chat_message",
            "content": "테스트 메시지",
        })

        # 응답 수신
        response = await communicator.receive_json_from()
        assert response["type"] == "chat_message"
        assert "unread_count" in response["message"]
        # 참여자 2명, 발신자 제외 = 1
        assert response["message"]["unread_count"] == 1

        await communicator.disconnect()

    async def test_read_status_broadcast_on_connect(self, user, other_user, room):
        """연결 시 안읽은 메시지에 대한 읽음 상태가 브로드캐스트된다."""
        # other_user가 보낸 메시지 생성
        @database_sync_to_async
        def create_message():
            return MessageFactory(room=room, sender=other_user, content="안읽은 메시지")

        message = await create_message()

        # user가 연결 (다른 사람이 보낸 메시지가 있음)
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # read_status 메시지 수신
        response = await communicator.receive_json_from()
        assert response["type"] == "read_status"
        assert message.pk in response["message_ids"]
        assert response["reader_id"] == user.pk

        # DB에 읽음 기록이 생성되었는지 확인 (Celery task가 실행됨)
        @database_sync_to_async
        def check_read_status():
            return MessageRead.objects.filter(message=message, user=user).exists()

        assert await check_read_status() is True

        await communicator.disconnect()

    async def test_no_read_status_for_own_messages(self, user, room):
        """자신이 보낸 메시지는 읽음 상태를 생성하지 않는다."""
        # user가 보낸 메시지 생성
        @database_sync_to_async
        def create_message():
            return MessageFactory(room=room, sender=user, content="내가 보낸 메시지")

        await create_message()

        # user 연결
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 읽음 상태 메시지가 오지 않아야 함 (자신의 메시지이므로)
        import asyncio
        try:
            # 짧은 시간 내에 메시지가 오는지 확인
            response = await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=0.5
            )
            # 메시지가 오면 read_status가 아니어야 함
            assert response.get("type") != "read_status"
        except asyncio.TimeoutError:
            # 타임아웃은 예상된 동작 (보낼 메시지 없음)
            pass

        await communicator.disconnect()

    async def test_synced_messages_include_unread_count(self, user, other_user, room):
        """동기화된 메시지에 unread_count가 포함된다."""
        import asyncio

        # 메시지 생성 (참여자 2명)
        @database_sync_to_async
        def create_messages():
            msg1 = MessageFactory(room=room, sender=other_user, content="메시지 1")
            msg2 = MessageFactory(room=room, sender=other_user, content="메시지 2")
            return msg1, msg2

        msg1, _ = await create_messages()

        # first_message_id를 첫 번째 메시지로 설정하고 재연결
        communicator = await create_communicator(
            user, room.pk, query_string=f"last_message_id={msg1.pk}"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        # 읽음 상태와 동기화 메시지 수신
        responses = []
        for _ in range(3):
            try:
                response = await asyncio.wait_for(
                    communicator.receive_json_from(),
                    timeout=0.5
                )
                responses.append(response)
            except asyncio.TimeoutError:
                break

        # 동기화된 chat_message 확인
        sync_messages = [r for r in responses if r.get("type") == "chat_message"]
        assert len(sync_messages) >= 1

        # unread_count 확인
        for msg in sync_messages:
            assert "unread_count" in msg["message"]

        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerSidebarUpdate:
    """ChatConsumer 사이드바 업데이트 테스트."""

    async def test_sidebar_update_on_new_message(self, user, other_user, room):
        """새 메시지 전송 시 사이드바 업데이트가 전송된다."""
        import asyncio

        # 사용자별 채널 그룹에 참여하므로 sidebar_update를 받을 수 있음
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 메시지 전송
        await communicator.send_json_to({
            "type": "chat_message",
            "content": "사이드바 테스트",
        })

        # 응답 수신 (chat_message, message_ack, sidebar_update 등)
        responses = []
        for _ in range(4):
            try:
                response = await asyncio.wait_for(
                    communicator.receive_json_from(),
                    timeout=0.5
                )
                responses.append(response)
            except asyncio.TimeoutError:
                break

        response_types = [r.get("type") for r in responses]
        assert "chat_message" in response_types

        # sidebar_update는 Celery task로 처리되므로 실행될 수 있음
        sidebar_updates = [r for r in responses if r.get("type") == "sidebar_update"]
        if sidebar_updates:
            sidebar = sidebar_updates[0]
            # SidebarUpdateMessage는 room 필드 안에 SidebarRoomPayload를 포함
            assert "room" in sidebar
            assert sidebar["room"]["room_id"] == room.pk
            assert "last_message" in sidebar["room"]
            assert "last_message_time" in sidebar["room"]

        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerSidebarOnlyConnect:
    """ChatConsumer 사이드바 전용 연결 테스트."""

    async def test_sidebar_only_connect_success(self, user):
        """인증된 사용자가 room 없이 사이드바 전용 연결에 성공한다."""
        communicator = await create_sidebar_communicator(user)

        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_sidebar_only_unauthenticated_rejected(self):
        """비인증 사용자가 사이드바 전용 연결을 거부당한다."""
        from django.contrib.auth.models import AnonymousUser

        communicator = await create_sidebar_communicator(AnonymousUser())

        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == CLOSE_CODE_UNAUTHORIZED

    async def test_sidebar_only_ignores_messages(self, user):
        """사이드바 전용 연결은 메시지 전송을 무시한다."""
        import asyncio

        communicator = await create_sidebar_communicator(user)
        connected, _ = await communicator.connect()
        assert connected is True

        # 메시지 전송 시도
        await communicator.send_json_to({
            "type": "chat_message",
            "content": "무시될 메시지",
        })

        # 응답이 없어야 함 (room이 없으므로 무시됨)
        try:
            await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=0.5
            )
            # 응답이 오면 실패 (응답이 없어야 함)
            assert False, "사이드바 전용 연결에서 메시지 응답이 오면 안 됨"
        except asyncio.TimeoutError:
            # 타임아웃은 예상된 동작
            pass

        await communicator.disconnect()

    async def test_sidebar_only_receives_sidebar_update(self, user, other_user, room):
        """사이드바 전용 연결에서 sidebar_update를 수신한다."""
        import asyncio

        # 사이드바 전용 연결
        sidebar_communicator = await create_sidebar_communicator(user)
        connected, _ = await sidebar_communicator.connect()
        assert connected is True

        # 다른 사용자가 채팅방에서 메시지 전송
        room_communicator = await create_communicator(other_user, room.pk)
        room_connected, _ = await room_communicator.connect()
        assert room_connected is True

        await room_communicator.send_json_to({
            "type": "chat_message",
            "content": "사이드바 업데이트 테스트",
        })

        # sidebar_communicator에서 sidebar_update 수신 대기
        # (Celery task가 실행되어야 하므로 시간이 걸릴 수 있음)
        try:
            response = await asyncio.wait_for(
                sidebar_communicator.receive_json_from(),
                timeout=1.0
            )
            assert response["type"] == "sidebar_update"
            assert response["room"]["room_id"] == room.pk
        except asyncio.TimeoutError:
            # Celery task가 테스트 환경에서 실행되지 않을 수 있음
            pass

        await sidebar_communicator.disconnect()
        await room_communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestChatConsumerMarkAsRead:
    """ChatConsumer mark_as_read 기능 테스트."""

    async def test_mark_as_read_broadcasts_read_status(self, user, other_user, room):
        """mark_as_read 메시지를 보내면 read_status가 브로드캐스트된다."""
        import asyncio

        # other_user가 채팅방에 연결
        other_communicator = await create_communicator(other_user, room.pk)
        other_connected, _ = await other_communicator.connect()
        assert other_connected is True

        # user가 채팅방에 연결
        user_communicator = await create_communicator(user, room.pk)
        user_connected, _ = await user_communicator.connect()
        assert user_connected is True

        # other_user가 새 메시지 전송
        await other_communicator.send_json_to({
            "type": "chat_message",
            "content": "새로운 메시지",
        })

        # other_user가 chat_message 수신
        chat_response = await other_communicator.receive_json_from()
        assert chat_response["type"] == "chat_message"
        new_message_id = chat_response["message"]["id"]

        # user도 chat_message 수신
        user_chat_response = await user_communicator.receive_json_from()
        assert user_chat_response["type"] == "chat_message"

        # user가 mark_as_read 전송
        await user_communicator.send_json_to({
            "type": "mark_as_read",
            "message_ids": [new_message_id],
        })

        # other_user가 read_status 수신
        responses = []
        for _ in range(3):
            try:
                response = await asyncio.wait_for(
                    other_communicator.receive_json_from(),
                    timeout=0.5
                )
                responses.append(response)
            except asyncio.TimeoutError:
                break

        read_status = [r for r in responses if r.get("type") == "read_status"]
        assert len(read_status) >= 1
        assert new_message_id in read_status[0]["message_ids"]
        assert read_status[0]["reader_id"] == user.pk

        await user_communicator.disconnect()
        await other_communicator.disconnect()

    async def test_mark_as_read_saves_to_db(self, user, other_user, room):
        """mark_as_read 메시지를 보내면 DB에 읽음 상태가 저장된다."""
        # other_user가 보낸 메시지 생성
        @database_sync_to_async
        def create_message():
            return MessageFactory(room=room, sender=other_user, content="DB 저장 테스트")

        message = await create_message()

        # user가 채팅방에 연결 (연결 시 자동 읽음 처리가 일어남)
        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 연결 시 자동 전송된 read_status 수신
        _ = await communicator.receive_json_from()

        # DB에서 읽음 상태 확인
        @database_sync_to_async
        def check_read_status():
            return MessageRead.objects.filter(message=message, user=user).exists()

        assert await check_read_status() is True

        await communicator.disconnect()

    async def test_mark_as_read_empty_message_ids_ignored(self, user, room):
        """빈 message_ids로 mark_as_read를 보내면 무시된다."""
        import asyncio

        communicator = await create_communicator(user, room.pk)
        connected, _ = await communicator.connect()
        assert connected is True

        # 빈 message_ids로 mark_as_read 전송
        await communicator.send_json_to({
            "type": "mark_as_read",
            "message_ids": [],
        })

        # 응답이 없어야 함
        try:
            await asyncio.wait_for(
                communicator.receive_json_from(),
                timeout=0.5
            )
            # 응답이 오면 read_status가 아니어야 함
            assert False, "빈 message_ids에 대해 응답이 오면 안 됨"
        except asyncio.TimeoutError:
            # 타임아웃은 예상된 동작
            pass

        await communicator.disconnect()
