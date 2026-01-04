from django.db import models

from rest_framework import serializers

from apps.chat.constants import MESSAGES_PER_PAGE
from apps.chat.models import Message


class MessageDirection(models.TextChoices):
    """메시지 조회 방향."""

    BEFORE = "before", "이전 메시지"
    AFTER = "after", "이후 메시지"
    AROUND = "around", "전후 메시지"


class MessageListParamsSerializer(serializers.Serializer):
    """메시지 목록 조회 파라미터.

    Query Parameters:
        direction: 조회 방향 (before|after|around)
        cursor: 기준 메시지 ID
        limit: 조회 개수
    """

    direction = serializers.ChoiceField(choices=MessageDirection.choices)
    cursor = serializers.IntegerField(min_value=1)
    limit = serializers.IntegerField(
        required=False,
        default=MESSAGES_PER_PAGE,
        min_value=1,
        max_value=MESSAGES_PER_PAGE * 2,
    )


class MessageSerializer(serializers.ModelSerializer):
    """메시지 직렬화."""

    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "content", "sender_id", "sender_name", "created_at"]
        read_only_fields = fields

    def get_sender_name(self, obj: Message) -> str:
        """발신자 이름 반환."""
        return obj.sender.name if obj.sender else "알 수 없음"
