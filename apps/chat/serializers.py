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
        direction: 조회 방향 (before|after|around). 기본값: before
        cursor: 기준 메시지 ID. 없으면 최신 메시지부터 조회
        limit: 조회 개수
    """

    direction = serializers.ChoiceField(
        choices=MessageDirection.choices,
        required=False,
        default=MessageDirection.BEFORE,
    )
    cursor = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    limit = serializers.IntegerField(
        required=False,
        default=MESSAGES_PER_PAGE,
        min_value=1,
        max_value=MESSAGES_PER_PAGE * 2,
    )


class MessageSerializer(serializers.ModelSerializer):
    """메시지 직렬화."""

    sender_name = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "content", "sender_id", "sender_name", "created_at", "unread_count"]
        read_only_fields = fields

    def get_sender_name(self, obj: Message) -> str:
        """발신자 이름 반환."""
        return obj.sender.name if obj.sender else "알 수 없음"

    def get_unread_count(self, obj: Message) -> int:
        """안읽은 인원 수 반환.

        with_unread_count()로 annotate된 경우 해당 값을 반환하고,
        그렇지 않으면 0을 반환.
        """
        return getattr(obj, "unread_count", 0)


class MessageSearchParamsSerializer(serializers.Serializer):
    """메시지 검색 파라미터.

    Query Parameters:
        q: 검색어 (최소 2자)
    """

    q = serializers.CharField(min_length=2, max_length=100)
