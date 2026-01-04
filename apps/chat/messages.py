from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter

from apps.chat.constants import MAX_MESSAGE_LENGTH
from apps.chat.enums import AckStatus, MessageType


class ChatSendMessage(BaseModel):
    """채팅 메시지 전송."""

    type: Literal[MessageType.CHAT_MESSAGE] = MessageType.CHAT_MESSAGE
    content: str = Field(..., max_length=MAX_MESSAGE_LENGTH)
    client_id: str | None = None


# TypeAdapter for parsing incoming messages
IncomingMessageAdapter: TypeAdapter[ChatSendMessage] = TypeAdapter(ChatSendMessage)


class MessagePayload(BaseModel):
    """채팅 메시지 페이로드."""

    id: int
    content: str
    sender_id: int
    sender_name: str
    created_at: str  # ISO 8601 format


class ChatReceivedMessage(BaseModel):
    """채팅 메시지 수신."""

    type: MessageType = MessageType.CHAT_MESSAGE
    message: MessagePayload


class MessageAckMessage(BaseModel):
    """메시지 전송 확인."""

    type: MessageType = MessageType.MESSAGE_ACK
    client_id: str
    message_id: int
    status: AckStatus = AckStatus.SUCCESS


class ErrorMessage(BaseModel):
    """에러 응답."""

    type: MessageType = MessageType.ERROR
    code: str
    message: str
