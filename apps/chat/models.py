from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import OuterRef, Prefetch, QuerySet, Subquery
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

import structlog

from apps.users.models import User

logger = structlog.get_logger(__name__)


class RoomQuerySet(QuerySet["Room"]):
    """Room 모델의 QuerySet."""

    def for_user(self, user: User) -> RoomQuerySet:
        """해당 사용자가 참여 중인 대화방을 반환한다."""
        return self.filter(participants=user)

    def ordered_by_updated(self) -> RoomQuerySet:
        """최근 업데이트 순으로 정렬한다."""
        return self.order_by("-updated_at")

    def with_latest_message(self) -> RoomQuerySet:
        """각 대화방의 최신 메시지를 prefetch한다.

        조회된 Room 인스턴스에서 get_last_message()로 접근 가능.
        """
        latest_message_subquery = (
            Message.objects.filter(room=OuterRef("pk"))
            .order_by("-created_at")
            .values("pk")[:1]
        )

        return self.prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.filter(
                    pk__in=Subquery(latest_message_subquery)
                ).select_related("sender"),
                to_attr="latest_messages",
            )
        )


class RoomManager(models.Manager["Room"]):
    """Room 모델의 커스텀 매니저."""

    @staticmethod
    def _generate_direct_chat_key(user1_id: int, user2_id: int) -> str:
        """두 사용자 ID로 정렬된 고유 키 생성."""
        min_id, max_id = sorted([user1_id, user2_id])
        return f"direct:{min_id}:{max_id}"

    def get_queryset(self) -> RoomQuerySet:
        return RoomQuerySet(self.model, using=self._db)

    def get_by_user(self, user: User) -> RoomQuerySet:
        """해당 사용자가 참여 중인 대화방을 최근 업데이트 순으로 반환한다."""
        return self.get_queryset().for_user(user).ordered_by_updated()

    def get_or_create_direct(self, user1: User, user2: User) -> Room:
        """두 사용자 간 1:1 대화방을 조회하거나 생성한다.

        이미 존재하는 1:1 대화방이 있으면 해당 대화방을 반환하고,
        없으면 새로 생성하여 반환한다.

        Unique 제약조건과 IntegrityError 처리로 동시성 문제를 해결한다.
        """
        key = self._generate_direct_chat_key(user1.pk, user2.pk)

        # 1. 먼저 조회
        existing_room = self.filter(direct_chat_key=key).first()
        if existing_room:
            return existing_room

        # 2. 없으면 생성 시도
        try:
            with transaction.atomic():
                room = self.model(
                    is_direct=True,
                    created_by=user1,
                    participant_count=2,
                    direct_chat_key=key,
                )
                room.save(using=self._db)
                room.participants.add(user1, user2)
                logger.info(
                    "direct_room_created",
                    room_id=room.pk,
                    user1_id=user1.pk,
                    user2_id=user2.pk,
                )
                return room
        except IntegrityError:
            # 3. 동시 생성 시 기존 방 반환
            logger.warning(
                "direct_room_creation_conflict",
                reason="integrity_error",
                user1_id=user1.pk,
                user2_id=user2.pk,
                direct_chat_key=key,
            )
            return self.get(direct_chat_key=key)

    def create_group(
        self, name: str, created_by: User, participants: list[User]
    ) -> Room:
        """그룹 대화방을 생성한다.

        Args:
            name: 대화방 이름
            created_by: 생성자
            participants: 참여자 목록 (생성자 미포함)

        Returns:
            생성된 Room 인스턴스
        """
        room = self.model(
            name=name,
            is_direct=False,
            created_by=created_by,
            participant_count=len(participants) + 1,  # 생성자 포함
        )
        room.save(using=self._db)
        room.participants.add(created_by, *participants)
        logger.info(
            "group_room_created",
            room_id=room.pk,
            room_name=name,
            created_by_id=created_by.pk,
            participant_count=len(participants) + 1,
        )
        return room


class Room(models.Model):
    """대화방 모델."""

    name = models.CharField("대화방 이름", max_length=100, blank=True)
    participants = models.ManyToManyField(
        User,
        verbose_name="참여자",
        related_name="chat_rooms",
    )
    participant_count = models.PositiveSmallIntegerField("참여자 수", default=0)
    is_direct = models.BooleanField("1:1 대화", default=True)
    direct_chat_key = models.CharField(
        "1:1 대화 키",
        max_length=50,
        unique=True,
        null=True,  # 그룹 대화는 null
        blank=True,
        db_index=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name="생성자",
        related_name="created_rooms",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    objects: RoomManager = RoomManager()

    class Meta:
        verbose_name = "대화방"
        verbose_name_plural = "대화방"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        if self.is_direct:
            return f"1:1 대화 ({self.pk})"
        return self.name or f"그룹 대화 ({self.pk})"

    def get_display_name(self, user: User) -> str:
        """주어진 사용자 기준으로 대화방 표시 이름을 반환한다.

        1:1 대화: 상대방 이름
        그룹 대화: 대화방 이름
        """
        if self.is_direct:
            other_user = self.get_other_participant(user)
            if other_user:
                return other_user.name
            return "알 수 없음"
        return self.name

    def get_other_participant(self, user: User) -> User | None:
        """1:1 대화에서 상대방을 반환한다. (prefetch 친화적)"""
        if not self.is_direct:
            return None
        # prefetch된 데이터를 Python 레벨에서 필터링
        for participant in self.participants.all():
            if participant.pk != user.pk:
                return participant
        return None

    def get_last_message(self) -> Message | None:
        """최신 메시지를 반환한다.

        with_latest_message()로 prefetch된 경우 캐시된 값을 반환하고,
        그렇지 않으면 DB 쿼리를 수행한다.
        """
        if hasattr(self, "latest_messages") and self.latest_messages:
            return self.latest_messages[0]
        return self.messages.order_by("-created_at").first()

    def is_participant(self, user: User) -> bool:
        """사용자가 대화방 참여자인지 확인한다."""
        return self.participants.filter(pk=user.pk).exists()


class MessageManager(models.Manager["Message"]):
    """Message 모델의 커스텀 매니저."""

    def get_by_room(self, room: Room) -> QuerySet[Message]:
        """해당 대화방의 메시지를 생성 시간 오름차순으로 반환한다."""
        return self.filter(room=room).select_related("sender").order_by("created_at")

    def create_message(self, room: Room, sender: User, content: str) -> Message:
        """새 메시지를 생성하고 대화방의 updated_at을 갱신한다.

        Args:
            room: 대화방
            sender: 발신자
            content: 메시지 내용

        Returns:
            생성된 Message 인스턴스
        """
        message = self.model(
            room=room,
            sender=sender,
            content=content,
        )
        message.full_clean()
        message.save(using=self._db)

        # 대화방의 updated_at 갱신
        room.save(update_fields=["updated_at"])

        return message


class Message(models.Model):
    """메시지 모델."""

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        verbose_name="대화방",
        related_name="messages",
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name="발신자",
        related_name="sent_messages",
        null=True,
        blank=True,
    )
    content = models.TextField("내용")
    created_at = models.DateTimeField("전송일시", auto_now_add=True)

    objects: MessageManager = MessageManager()

    class Meta:
        verbose_name = "메시지"
        verbose_name_plural = "메시지"
        ordering = ["created_at"]

    def __str__(self) -> str:
        sender_name = self.sender.name if self.sender else "알 수 없음"
        return f"{sender_name}: {self.content[:30]}"

    def clean(self) -> None:
        """빈 메시지 검증."""
        if not self.content or not self.content.strip():
            raise ValidationError({"content": "메시지 내용은 필수입니다."})

    def get_preview(self, max_length: int = 50) -> str:
        """메시지 미리보기를 반환한다."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."


# Signals
@receiver(m2m_changed, sender=Room.participants.through)
def update_participant_count(
    sender: type, instance: Room, action: str, **kwargs
) -> None:
    """participants M2M 변경 시 participant_count 자동 갱신."""
    if action in ("post_add", "post_remove", "post_clear"):
        instance.participant_count = instance.participants.count()
        instance.save(update_fields=["participant_count"])
