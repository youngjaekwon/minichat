from enum import StrEnum


class MessageType(StrEnum):
    """WebSocket 메시지 타입."""

    CHAT_MESSAGE = "chat_message"
    MESSAGE_ACK = "message_ack"
    ERROR = "error"
    READ_STATUS = "read_status"
    SIDEBAR_UPDATE = "sidebar_update"


class AckStatus(StrEnum):
    """메시지 ACK 상태."""

    SUCCESS = "success"
