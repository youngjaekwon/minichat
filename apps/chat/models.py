from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Count, OuterRef, Prefetch, QuerySet, Subquery
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

import structlog

from apps.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet as QS

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

    def get_by_user_paginated(
        self,
        user: User,
        cursor: datetime | None = None,
        limit: int = 20,
    ) -> tuple[list[Room], bool, datetime | None]:
        """사용자의 대화방 목록을 페이지네이션하여 반환한다.

        Args:
            user: 사용자
            cursor: 커서 기준 시간 (이 시간보다 이전 데이터 조회)
            limit: 조회 개수

        Returns:
            (rooms, has_more, next_cursor) 튜플
        """
        queryset = (
            self.get_by_user(user)
            .prefetch_related("participants")
            .with_latest_message()
        )

        if cursor:
            queryset = queryset.filter(updated_at__lt=cursor)

        # limit+1 조회하여 has_more 판단
        rooms = list(queryset[: limit + 1])

        has_more = len(rooms) > limit
        if has_more:
            rooms = rooms[:limit]

        # next_cursor 생성
        next_cursor = rooms[-1].updated_at if has_more and rooms else None

        return rooms, has_more, next_cursor

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

    def search_by_message(
        self,
        user: User,
        query: str,
        cursor: datetime | None = None,
        limit: int = 20,
    ) -> tuple[list[dict], bool, datetime | None]:
        """메시지 내용으로 대화방을 검색한다.

        사용자가 참여 중인 대화방의 메시지에서 검색어를 찾고,
        일치하는 메시지가 있는 대화방 목록을 반환한다.

        Args:
            user: 검색하는 사용자
            query: 검색어
            cursor: 커서 기준 시간 (이 시간보다 이전 데이터 조회)
            limit: 조회 개수

        Returns:
            (results, has_more, next_cursor) 튜플
        """
        # 사용자가 참여 중인 대화방 ID 목록
        user_room_ids = user.chat_rooms.values_list("id", flat=True)

        # 각 대화방에서 검색어가 포함된 가장 최신 메시지의 ID를 서브쿼리로 조회
        latest_msg_id_subquery = (
            Message.objects.filter(
                room_id=OuterRef("room_id"),
                content__icontains=query,
            )
            .order_by("-created_at")
            .values("id")[:1]
        )

        # DB 레벨에서 룸당 최신 메시지 하나만 조회
        matching_message_ids = (
            Message.objects.filter(
                room_id__in=user_room_ids,
                content__icontains=query,
            )
            .values("room_id")
            .distinct()
            .annotate(latest_id=Subquery(latest_msg_id_subquery))
            .values_list("latest_id", flat=True)
        )

        matching_messages = (
            Message.objects.filter(id__in=matching_message_ids)
            .select_related("room")
            .prefetch_related("room__participants")
            .order_by("-created_at")
        )

        # 커서 기반 필터링
        if cursor:
            matching_messages = matching_messages.filter(created_at__lt=cursor)

        # limit+1 조회하여 has_more 판단
        messages = list(matching_messages[: limit + 1])

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        results = [
            {
                "room": message.room,
                "display_name": message.room.get_display_name(user),
                "matched_message_preview": message.get_matched_preview(query),
                "matched_message_created_at": message.created_at,
            }
            for message in messages
        ]

        # next_cursor 생성
        next_cursor = (
            results[-1]["matched_message_created_at"] if has_more and results else None
        )

        return results, has_more, next_cursor


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


class MessageQuerySet(QuerySet["Message"]):
    """Message 모델의 QuerySet."""

    def for_room(self, room: Room) -> MessageQuerySet:
        """해당 대화방의 메시지를 반환한다."""
        return self.filter(room=room)

    def search(self, query: str) -> MessageQuerySet:
        """메시지 내용에서 키워드를 검색한다.

        pg_trgm + GIN 인덱스를 활용한 부분 일치 검색.
        """
        return self.filter(content__icontains=query)

    def before_cursor(self, cursor_id: int) -> MessageQuerySet:
        """주어진 ID보다 작은(오래된) 메시지를 반환한다."""
        return self.filter(pk__lt=cursor_id)

    def after_cursor(self, cursor_id: int) -> MessageQuerySet:
        """주어진 ID보다 큰(최신) 메시지를 반환한다."""
        return self.filter(pk__gt=cursor_id)

    def ordered_by_created_desc(self) -> MessageQuerySet:
        """생성 시간 내림차순 정렬 (최신순)."""
        return self.order_by("-created_at", "-pk")

    def ordered_by_created_asc(self) -> MessageQuerySet:
        """생성 시간 오름차순 정렬."""
        return self.order_by("created_at", "pk")

    def with_sender(self) -> MessageQuerySet:
        """sender를 select_related로 조회."""
        return self.select_related("sender")

    def with_unread_count(self) -> MessageQuerySet:
        """메시지별 안읽은 인원 수를 annotate한다.

        unread_count = 대화방 참여자 수 - 읽은 사람 수 - 1 (발신자 제외)
        """
        return self.annotate(
            read_count=Count("reads"),
            unread_count=models.F("room__participant_count")
            - models.F("read_count")
            - 1,  # 발신자 제외
        )


class MessageManager(models.Manager["Message"]):
    """Message 모델의 커스텀 매니저."""

    def get_queryset(self) -> MessageQuerySet:
        return MessageQuerySet(self.model, using=self._db)

    def get_by_room(self, room: Room) -> MessageQuerySet:
        """해당 대화방의 메시지를 생성 시간 오름차순으로 반환한다."""
        return (
            self.get_queryset()
            .for_room(room)
            .with_sender()
            .with_unread_count()
            .ordered_by_created_asc()
        )

    def get_latest_messages(self, room: Room, limit: int) -> list[Message]:
        """해당 대화방의 최신 메시지를 limit 개수만큼 반환한다.

        Returns:
            최신순으로 조회 후 시간순으로 정렬된 리스트
        """
        messages = list(
            self.get_queryset()
            .for_room(room)
            .with_sender()
            .with_unread_count()
            .ordered_by_created_desc()[:limit]
        )
        return list(reversed(messages))

    def get_messages_before(
        self, room: Room, cursor_id: int, limit: int
    ) -> tuple[list[Message], bool]:
        """cursor_id 이전의 메시지를 조회한다.

        Args:
            room: 대화방
            cursor_id: 기준 메시지 ID
            limit: 조회 개수

        Returns:
            (메시지 리스트, has_more 여부) 튜플
        """
        messages = list(
            self.get_queryset()
            .for_room(room)
            .before_cursor(cursor_id)
            .with_sender()
            .with_unread_count()
            .ordered_by_created_desc()[: limit + 1]
        )

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        return list(reversed(messages)), has_more

    def get_messages_after(
        self, room: Room, cursor_id: int, limit: int
    ) -> tuple[list[Message], bool]:
        """cursor_id 이후의 메시지를 조회한다.

        Args:
            room: 대화방
            cursor_id: 기준 메시지 ID
            limit: 조회 개수

        Returns:
            (메시지 리스트, has_more 여부) 튜플
            - 메시지는 시간순 정렬 (오래된 것 먼저)
        """
        messages = list(
            self.get_queryset()
            .for_room(room)
            .after_cursor(cursor_id)
            .with_sender()
            .with_unread_count()
            .ordered_by_created_asc()[: limit + 1]
        )

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        return messages, has_more

    def get_messages_around(
        self, room: Room, cursor_id: int, limit: int
    ) -> tuple[list[Message], bool, bool]:
        """cursor_id 전후의 메시지를 조회한다.

        Args:
            room: 대화방
            cursor_id: 기준 메시지 ID (이 메시지 포함)
            limit: 조회 개수 (기준 메시지 포함)

        Returns:
            (메시지 리스트, has_more_before, has_more_after) 튜플
            - 메시지는 시간순 정렬 (오래된 것 먼저)
        """
        half = limit // 2

        # 기준 메시지 포함 이전 메시지 (내림차순 조회 후 reverse)
        before_messages = list(
            self.get_queryset()
            .for_room(room)
            .filter(pk__lte=cursor_id)
            .with_sender()
            .with_unread_count()
            .ordered_by_created_desc()[: half + 2]
        )
        has_more_before = len(before_messages) > half + 1
        if has_more_before:
            before_messages = before_messages[: half + 1]
        before_messages = list(reversed(before_messages))

        # 기준 메시지 이후 메시지 (기준 메시지 제외)
        after_messages = list(
            self.get_queryset()
            .for_room(room)
            .after_cursor(cursor_id)
            .with_sender()
            .with_unread_count()
            .ordered_by_created_asc()[: half + 1]
        )
        has_more_after = len(after_messages) > half
        if has_more_after:
            after_messages = after_messages[:half]

        return before_messages + after_messages, has_more_before, has_more_after

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
        indexes = [
            GinIndex(
                name="message_content_trigram_idx",
                fields=["content"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self) -> str:
        sender_name = self.sender.name if self.sender else "알 수 없음"
        return f"{sender_name}: {self.content[:30]}"

    def clean(self) -> None:
        """빈 메시지 검증."""
        if not self.content or not self.content.strip():
            raise ValidationError({"content": "메시지 내용은 필수입니다."})

    def get_preview(self, max_length: int = 20) -> str:
        """메시지 미리보기를 반환한다."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

    def get_matched_preview(self, query: str, max_length: int = 20) -> str:
        """검색어와 일치하는 부분의 메시지 미리보기를 반환한다."""
        content = self.content
        query_lower = query.lower()
        content_lower = content.lower()

        # 검색어 위치 찾기
        index = content_lower.find(query_lower)
        if index == -1:
            return self.get_preview(max_length)

        # 검색어 중심으로 앞뒤 컨텍스트 포함
        query_len = len(query)
        context_len = (max_length - query_len) // 2

        start = max(0, index - context_len)
        end = min(len(content), index + query_len + context_len)

        preview = content[start:end]

        # 앞뒤 말줄임 처리
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."

        return preview


# Signals
@receiver(m2m_changed, sender=Room.participants.through)
def update_participant_count(
    sender: type, instance: Room, action: str, **kwargs
) -> None:
    """participants M2M 변경 시 participant_count 자동 갱신."""
    if action in ("post_add", "post_remove", "post_clear"):
        instance.participant_count = instance.participants.count()
        instance.save(update_fields=["participant_count"])


class MessageReadManager(models.Manager["MessageRead"]):
    """MessageRead 모델의 커스텀 매니저."""

    def mark_as_read(self, room: Room, user: User) -> tuple[list[int], list[int]]:
        """대화방의 안읽은 메시지를 일괄 읽음 처리한다.

        Args:
            room: 대화방
            user: 읽음 처리할 사용자

        Returns:
            (읽음 처리된 메시지 ID 목록, 해당 메시지 발신자 ID 목록) 튜플
        """
        # 자신이 보낸 메시지를 제외한 안읽은 메시지 조회
        unread_messages = (
            Message.objects.filter(room=room)
            .exclude(sender=user)
            .exclude(reads__user=user)
            .select_related("sender")
        )

        message_ids: list[int] = []
        sender_ids: set[int] = set()

        # 읽음 기록 생성
        read_records = []
        for message in unread_messages:
            read_records.append(
                self.model(message=message, user=user)
            )
            message_ids.append(message.pk)
            if message.sender_id:
                sender_ids.add(message.sender_id)

        if read_records:
            self.bulk_create(read_records, ignore_conflicts=True)
            logger.info(
                "messages_marked_as_read",
                room_id=room.pk,
                user_id=user.pk,
                message_count=len(message_ids),
            )

        return message_ids, list(sender_ids)

    def get_unread_count(self, room: Room, user: User) -> int:
        """사용자의 해당 방 안읽은 메시지 수를 반환한다."""
        return (
            Message.objects.filter(room=room)
            .exclude(sender=user)
            .exclude(reads__user=user)
            .count()
        )

    def get_unread_counts_for_rooms(
        self, rooms: QS[Room], user: User
    ) -> dict[int, int]:
        """여러 채팅방의 안읽은 메시지 수를 한 번에 조회한다.

        Args:
            rooms: 채팅방 QuerySet
            user: 사용자

        Returns:
            {room_id: unread_count} 딕셔너리
        """
        room_ids = [room.pk for room in rooms]

        # 각 방별 안읽은 메시지 수 집계
        unread_counts = (
            Message.objects.filter(room_id__in=room_ids)
            .exclude(sender=user)
            .exclude(reads__user=user)
            .values("room_id")
            .annotate(count=Count("pk"))
        )

        return {item["room_id"]: item["count"] for item in unread_counts}


class MessageRead(models.Model):
    """메시지 읽음 기록 모델."""

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name="메시지",
        related_name="reads",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="사용자",
        related_name="read_messages",
    )
    read_at = models.DateTimeField("읽은 시간", auto_now_add=True)

    objects: MessageReadManager = MessageReadManager()

    class Meta:
        verbose_name = "메시지 읽음 기록"
        verbose_name_plural = "메시지 읽음 기록"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_message_read",
            )
        ]
        indexes = [
            models.Index(fields=["message", "user"]),
            models.Index(fields=["user", "read_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.message_id}"
