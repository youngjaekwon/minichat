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


class MarkAsReadMessage(BaseModel):
    """메시지 읽음 처리 요청."""

    type: Literal[MessageType.MARK_AS_READ] = MessageType.MARK_AS_READ
    message_ids: list[int]


# TypeAdapter for parsing incoming messages (Union of all incoming types)
IncomingMessage = ChatSendMessage | MarkAsReadMessage
IncomingMessageAdapter: TypeAdapter[IncomingMessage] = TypeAdapter(IncomingMessage)


class MessagePayload(BaseModel):
    """채팅 메시지 페이로드."""

    id: int
    content: str
    sender_id: int
    sender_name: str
    created_at: str  # ISO 8601 format
    unread_count: int = 0  # 안읽은 참여자 수


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


class ReadStatusMessage(BaseModel):
    """읽음 상태 변경 알림.

    메시지 발신자에게 자신의 메시지가 읽혔음을 알림.
    """

    type: MessageType = MessageType.READ_STATUS
    room_id: int
    message_ids: list[int]
    reader_id: int


class SidebarRoomPayload(BaseModel):
    """사이드바 채팅방 정보."""

    room_id: int
    last_message: str | None = None
    last_message_time: str | None = None  # ISO 8601 format
    unread_count: int = 0


class SidebarUpdateMessage(BaseModel):
    """사이드바 갱신 알림.

    새 메시지 수신 또는 읽음 상태 변경 시 사이드바 업데이트.
    """

    type: MessageType = MessageType.SIDEBAR_UPDATE
    room: SidebarRoomPayload


# HTTP API 응답 타입


class MessageListResponse(BaseModel):
    """before/after API 응답."""

    messages: list[MessagePayload]
    has_more: bool
    next_cursor: int | None


class MessageAroundResponse(BaseModel):
    """around API 응답."""

    messages: list[MessagePayload]
    has_more_before: bool
    has_more_after: bool
    next_cursor_before: int | None
    next_cursor_after: int | None
    target_message_id: int
