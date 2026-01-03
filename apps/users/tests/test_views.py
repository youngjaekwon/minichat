from django.urls import reverse

import pytest

from tests.factories import UserFactory


@pytest.mark.django_db
class TestSignupView:
    def test_signup_page_renders(self, client):
        """회원가입 페이지 렌더링 테스트"""
        response = client.get(reverse("users:signup"))

        assert response.status_code == 200
        assert "회원가입" in response.content.decode()

    def test_signup_success(self, client):
        """회원가입 성공 테스트"""
        response = client.post(
            reverse("users:signup"),
            {
                "email": "signup@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "name": "신규 사용자",
            },
        )

        assert response.status_code == 302
        assert response.url == "/"

    def test_signup_password_mismatch(self, client):
        """비밀번호 불일치 테스트"""
        response = client.post(
            reverse("users:signup"),
            {
                "email": "mismatch@example.com",
                "password": "SecurePass123!",
                "password_confirm": "DifferentPass!",
                "name": "불일치 테스트",
            },
        )

        assert response.status_code == 200
        assert "비밀번호가 일치하지 않습니다" in response.content.decode()

    def test_signup_duplicate_email(self, client):
        """중복 이메일 회원가입 테스트"""
        UserFactory(email="duplicate@example.com")

        response = client.post(
            reverse("users:signup"),
            {
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "name": "중복 테스트",
            },
        )

        assert response.status_code == 200
        assert "이메일" in response.content.decode()

    def test_authenticated_user_redirected(self, client):
        """인증된 사용자 리다이렉트 테스트"""
        user = UserFactory(email="auth@example.com", password="testpass123!")
        client.force_login(user)

        response = client.get(reverse("users:signup"))

        assert response.status_code == 302
        assert response.url == "/"


@pytest.mark.django_db
class TestLoginView:
    def test_login_page_renders(self, client):
        """로그인 페이지 렌더링 테스트"""
        response = client.get(reverse("users:login"))

        assert response.status_code == 200
        assert "로그인" in response.content.decode()

    def test_login_success(self, client):
        """로그인 성공 테스트"""
        UserFactory(email="logintest@example.com", password="testpass123!")

        response = client.post(
            reverse("users:login"),
            {
                "email": "logintest@example.com",
                "password": "testpass123!",
            },
        )

        assert response.status_code == 302
        assert response.url == "/"

    def test_login_wrong_password(self, client):
        """잘못된 비밀번호 로그인 테스트"""
        UserFactory(email="wrongpass@example.com", password="correctpass!")

        response = client.post(
            reverse("users:login"),
            {
                "email": "wrongpass@example.com",
                "password": "wrongpass!",
            },
        )

        assert response.status_code == 200
        assert "올바르지 않습니다" in response.content.decode()

    def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자 로그인 테스트"""
        response = client.post(
            reverse("users:login"),
            {
                "email": "notexist@example.com",
                "password": "anypass!",
            },
        )

        assert response.status_code == 200
        assert "올바르지 않습니다" in response.content.decode()

    def test_authenticated_user_redirected(self, client):
        """인증된 사용자 리다이렉트 테스트"""
        user = UserFactory(email="loggedin@example.com", password="testpass123!")
        client.force_login(user)

        response = client.get(reverse("users:login"))

        assert response.status_code == 302
        assert response.url == "/"


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_success(self, client):
        """로그아웃 성공 테스트"""
        user = UserFactory(email="logout@example.com", password="testpass123!")
        client.force_login(user)

        response = client.post(reverse("users:logout"))

        assert response.status_code == 302
        assert response.url == reverse("users:login")

    def test_logout_get_request_rejected(self, client):
        """로그아웃 GET 요청 거부 테스트 (CSRF 보호)"""
        user = UserFactory(email="logout_get@example.com", password="testpass123!")
        client.force_login(user)

        response = client.get(reverse("users:logout"))

        assert response.status_code == 405  # Method Not Allowed
