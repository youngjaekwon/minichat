"""
factory-boy 팩토리 정의

테스트 데이터 생성을 위한 팩토리 클래스를 정의한다.
"""

import factory

from apps.chat.models import Message, MessageRead, Room
from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """User 모델 팩토리"""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name", locale="ko_KR")
    job_title = factory.Faker("job", locale="ko_KR")
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "testpass123!"
        self.set_password(password)
        if create:
            self.save()


class RoomFactory(factory.django.DjangoModelFactory):
    """Room 모델 팩토리"""

    class Meta:
        model = Room
        skip_postgeneration_save = True

    name = ""
    is_direct = True
    created_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def participants(self, create, extracted, **kwargs):
        if not create:
            return

        # 생성자를 참여자에 추가
        self.participants.add(self.created_by)
        count = 1

        if extracted:
            for user in extracted:
                self.participants.add(user)
                count += 1

        # participant_count 업데이트
        self.participant_count = count

        # 1:1 대화방이고 참여자가 2명이면 direct_chat_key 생성
        if self.is_direct and count == 2:
            participant_ids = sorted(
                self.participants.values_list("id", flat=True)
            )
            self.direct_chat_key = f"direct:{participant_ids[0]}:{participant_ids[1]}"
            self.save(update_fields=["participant_count", "direct_chat_key"])
        else:
            self.save(update_fields=["participant_count"])


class MessageFactory(factory.django.DjangoModelFactory):
    """Message 모델 팩토리"""

    class Meta:
        model = Message

    room = factory.SubFactory(RoomFactory)
    sender = factory.SubFactory(UserFactory)
    content = factory.Faker("text", max_nb_chars=200, locale="ko_KR")


class MessageReadFactory(factory.django.DjangoModelFactory):
    """MessageRead 모델 팩토리"""

    class Meta:
        model = MessageRead

    message = factory.SubFactory(MessageFactory)
    user = factory.SubFactory(UserFactory)
