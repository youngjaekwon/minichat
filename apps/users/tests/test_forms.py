import pytest

from apps.users.forms import LoginForm, SignupForm
from apps.users.models import User


@pytest.mark.django_db
class TestSignupForm:
    """SignupForm 테스트"""

    def test_valid_form(self):
        """유효한 폼 테스트"""
        form = SignupForm(
            data={
                "email": "test@example.com",
                "name": "테스트",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            }
        )
        assert form.is_valid()

    def test_password_mismatch(self):
        """비밀번호 불일치 테스트"""
        form = SignupForm(
            data={
                "email": "test@example.com",
                "name": "테스트",
                "password": "SecurePass123!",
                "password_confirm": "DifferentPass123!",
            }
        )
        assert not form.is_valid()
        assert "password_confirm" in form.errors

    def test_weak_password(self):
        """약한 비밀번호 테스트"""
        form = SignupForm(
            data={
                "email": "test@example.com",
                "name": "테스트",
                "password": "123",
                "password_confirm": "123",
            }
        )
        assert not form.is_valid()
        assert "password" in form.errors

    def test_invalid_email(self):
        """잘못된 이메일 형식 테스트"""
        form = SignupForm(
            data={
                "email": "invalid-email",
                "name": "테스트",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            }
        )
        assert not form.is_valid()
        assert "email" in form.errors

    def test_required_fields(self):
        """필수 필드 테스트"""
        form = SignupForm(data={})
        assert not form.is_valid()
        assert "email" in form.errors
        assert "name" in form.errors
        assert "password" in form.errors
        assert "password_confirm" in form.errors


@pytest.mark.django_db
class TestSignupFormSave:
    """SignupForm.save() 테스트"""

    def test_save_creates_user(self):
        """save()가 사용자를 생성하는지 테스트"""
        form = SignupForm(
            data={
                "email": "save@example.com",
                "name": "저장 테스트",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            }
        )
        assert form.is_valid()
        user = form.save()

        assert user.pk is not None
        assert user.email == "save@example.com"
        assert user.name == "저장 테스트"
        assert user.check_password("SecurePass123!")

    def test_save_with_job_title(self):
        """직업/소속과 함께 사용자 생성 테스트"""
        form = SignupForm(
            data={
                "email": "job@example.com",
                "name": "직업 테스트",
                "job_title": "개발자",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            }
        )
        assert form.is_valid()
        user = form.save()

        assert user.job_title == "개발자"

    def test_duplicate_email_validation(self):
        """중복 이메일 시 폼 유효성 검사 실패 테스트"""
        user = User.objects.create_user(
            email="duplicate@example.com",
            password="test123!",
            name="기존 사용자",
        )
        user.save()

        form = SignupForm(
            data={
                "email": "duplicate@example.com",
                "name": "중복 테스트",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            }
        )
        assert not form.is_valid()
        assert "email" in form.errors
        assert "이미 사용 중인 이메일입니다." in str(form.errors["email"])


@pytest.mark.django_db
class TestLoginForm:
    """LoginForm 테스트"""

    def test_valid_form(self):
        """유효한 폼 테스트 - 실제 사용자로 인증"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123!",
            name="Test User",
        )
        user.save()

        form = LoginForm(
            data={
                "email": "test@example.com",
                "password": "testpass123!",
            }
        )
        assert form.is_valid()
        assert form.get_user() is not None

    def test_invalid_email(self):
        """잘못된 이메일 형식 테스트"""
        form = LoginForm(
            data={
                "email": "invalid-email",
                "password": "testpass123!",
            }
        )
        assert not form.is_valid()
        assert "email" in form.errors

    def test_required_fields(self):
        """필수 필드 테스트"""
        form = LoginForm(data={})
        assert not form.is_valid()
        assert "email" in form.errors
        assert "password" in form.errors
