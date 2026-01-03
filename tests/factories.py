"""
factory-boy 팩토리 정의

테스트 데이터 생성을 위한 팩토리 클래스를 정의한다.
"""

import factory

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
