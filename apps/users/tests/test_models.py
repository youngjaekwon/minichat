from io import BytesIO

from django.core.exceptions import ValidationError

import pytest
from PIL import Image

from apps.users.models import User
from tests.factories import UserFactory


def create_test_image(width: int = 500, height: int = 500) -> BytesIO:
    """테스트용 이미지 생성"""
    image = Image.new("RGB", (width, height), color="red")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    buffer.name = "test.jpg"
    return buffer


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        """일반 사용자 생성 테스트"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123!",
            name="테스트 사용자",
        )

        assert user.email == "test@example.com"
        assert user.name == "테스트 사용자"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("testpass123!")

    def test_create_user_without_email_raises_error(self):
        """이메일 없이 사용자 생성 시 에러"""
        with pytest.raises(ValueError, match="이메일은 필수입니다"):
            User.objects.create_user(email="", password="testpass123!", name="테스트")

    def test_email_is_normalized(self):
        """이메일 정규화 테스트"""
        user = User.objects.create_user(
            email="Test@EXAMPLE.com",
            password="testpass123!",
            name="테스트",
        )

        assert user.email == "Test@example.com"

    def test_email_unique_constraint(self):
        """이메일 중복 제약 조건 테스트 - IntegrityError 발생"""
        from django.db import IntegrityError

        user1 = User.objects.create_user(
            email="duplicate@example.com",
            password="testpass123!",
            name="첫 번째",
        )
        user1.save()

        user2 = User.objects.create_user(
            email="duplicate@example.com",
            password="testpass123!",
            name="두 번째",
        )

        with pytest.raises(IntegrityError):
            user2.save()

    def test_user_str(self):
        """User __str__ 메서드 테스트"""
        user = UserFactory(email="str@example.com")
        assert str(user) == "str@example.com"


@pytest.mark.django_db
class TestUserManagerCreateUser:
    """User.objects.create_user() 확장 기능 테스트"""

    def test_user_create_success(self):
        """사용자 생성 성공 테스트"""
        user = User.objects.create_user(
            email="new@example.com",
            password="SecurePass123!",
            name="새 사용자",
            job_title="개발자",
        )

        assert user.email == "new@example.com"
        assert user.name == "새 사용자"
        assert user.job_title == "개발자"
        assert user.check_password("SecurePass123!")

    def test_user_create_with_profile_image(self):
        """프로필 이미지와 함께 사용자 생성 테스트 (리사이징 포함)"""
        # 큰 이미지로 테스트 (1000x800)
        image_file = create_test_image(1000, 800)
        user = User.objects.create_user(
            email="image@example.com",
            password="SecurePass123!",
            name="이미지 사용자",
            profile_image=image_file,
        )

        assert user.profile_image
        assert user.profile_image.name.endswith(".jpg")

        # 리사이징 검증 (300x300 이하로 축소)
        resized_image = Image.open(user.profile_image)
        assert resized_image.width <= 300
        assert resized_image.height <= 300

    def test_user_create_with_profile_image_preserves_aspect_ratio(self):
        """프로필 이미지 리사이징 시 종횡비 유지 테스트"""
        # 2:1 비율 이미지 (1000x500)
        image_file = create_test_image(1000, 500)
        user = User.objects.create_user(
            email="ratio@example.com",
            password="SecurePass123!",
            name="비율 테스트",
            profile_image=image_file,
        )

        resized_image = Image.open(user.profile_image)
        assert resized_image.width == 300
        assert resized_image.height == 150

    def test_user_create_duplicate_email_raises_integrity_error(self):
        """중복 이메일로 저장 시 IntegrityError 발생 테스트"""
        from django.db import IntegrityError

        UserFactory(email="exists@example.com")

        user = User.objects.create_user(
            email="exists@example.com",
            password="SecurePass123!",
            name="중복 사용자",
        )

        with pytest.raises(IntegrityError):
            user.save()


@pytest.mark.django_db
class TestUserManagerSelectors:
    """User.objects.get_by_* 메서드 테스트"""

    def test_get_by_email_found(self):
        """이메일로 사용자 조회 성공 테스트"""
        UserFactory(email="found@example.com")
        user = User.objects.get_by_email("found@example.com")
        assert user is not None
        assert user.email == "found@example.com"

    def test_get_by_email_not_found(self):
        """존재하지 않는 이메일 조회 테스트"""
        user = User.objects.get_by_email("notfound@example.com")
        assert user is None

    def test_get_by_email_case_insensitive(self):
        """이메일 대소문자 구분 없이 조회 테스트"""
        UserFactory(email="CaseTest@example.com")
        user = User.objects.get_by_email("casetest@example.com")
        assert user is not None

    def test_get_by_id_found(self):
        """ID로 사용자 조회 성공 테스트"""
        created_user = UserFactory()
        user = User.objects.get_by_id(created_user.pk)
        assert user is not None
        assert user.pk == created_user.pk

    def test_get_by_id_not_found(self):
        """존재하지 않는 ID 조회 테스트"""
        user = User.objects.get_by_id(99999)
        assert user is None


