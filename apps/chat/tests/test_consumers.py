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
from apps.chat.models import Message
from tests.factories import MessageFactory, RoomFactory, UserFactory


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
