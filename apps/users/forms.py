from typing import Any

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

import structlog
from PIL import Image

from apps.users.constants import (
    PROFILE_IMAGE_ALLOWED_FORMATS,
    PROFILE_IMAGE_MAX_PIXELS,
    PROFILE_IMAGE_MAX_UPLOAD_SIZE,
)
from apps.users.models import User


class SignupForm(forms.ModelForm):
    """회원가입 폼."""

    password = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput,
        error_messages={
            "required": "비밀번호를 입력해주세요.",
        },
    )
    password_confirm = forms.CharField(
        label="비밀번호 확인",
        widget=forms.PasswordInput,
        error_messages={
            "required": "비밀번호 확인을 입력해주세요.",
        },
    )

    class Meta:
        model = User
        fields = ["email", "name", "job_title", "profile_image"]
        error_messages = {
            "email": {
                "required": "이메일을 입력해주세요.",
                "invalid": "올바른 이메일 형식이 아닙니다.",
            },
            "name": {
                "required": "이름을 입력해주세요.",
            },
        }

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                User._meta.get_field("email").error_messages["unique"]
            )
        return email

    def clean_profile_image(self):
        image = self.cleaned_data.get("profile_image")
        if not image:
            return image

        # 파일 크기 검증
        if image.size > PROFILE_IMAGE_MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"이미지 파일이 너무 큽니다. (최대 {PROFILE_IMAGE_MAX_UPLOAD_SIZE // (1024 * 1024)}MB)"
            )

        # 이미지 형식 및 픽셀 크기 검증
        try:
            img = Image.open(image)

            if img.format not in PROFILE_IMAGE_ALLOWED_FORMATS:
                raise forms.ValidationError(
                    f"지원하지 않는 이미지 형식입니다. "
                    f"허용: {', '.join(PROFILE_IMAGE_ALLOWED_FORMATS)}"
                )

            if img.width * img.height > PROFILE_IMAGE_MAX_PIXELS:
                raise forms.ValidationError(
                    f"이미지 해상도가 너무 높습니다. "
                    f"(최대 {PROFILE_IMAGE_MAX_PIXELS // 1_000_000}MP)"
                )

            img.verify()
            image.seek(0)

        except OSError as e:
            raise forms.ValidationError("유효하지 않은 이미지 파일입니다.") from e

        return image

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages) from e
        return password

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "비밀번호가 일치하지 않습니다.")

        return cleaned_data

    def save(self, commit: bool = True) -> User:
        """사용자를 생성한다."""
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            name=self.cleaned_data["name"],
            profile_image=self.cleaned_data.get("profile_image"),
            job_title=self.cleaned_data.get("job_title", ""),
        )

        if commit:
            user.save()
            structlog.contextvars.bind_contextvars(
                action="user_create",
                success=True,
                user_id=user.pk,
            )

        return user


class LoginForm(forms.Form):
    """로그인 폼 (Django AuthenticationForm 호환)."""

    email = forms.EmailField(
        label="이메일",
        widget=forms.EmailInput(attrs={"autofocus": True}),
        error_messages={
            "required": "이메일을 입력해주세요.",
            "invalid": "올바른 이메일 형식이 아닙니다.",
        },
    )
    password = forms.CharField(
        label="비밀번호",
        strip=False,
        widget=forms.PasswordInput,
        error_messages={
            "required": "비밀번호를 입력해주세요.",
        },
    )

    error_messages = {
        "invalid_login": "이메일 또는 비밀번호가 올바르지 않습니다.",
        "inactive": "이 계정은 비활성화되어 있습니다.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any]:
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")

        if email is not None and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    self.error_messages["inactive"],
                    code="inactive",
                )

        return self.cleaned_data

    def get_user(self) -> User | None:
        return self.user_cache
