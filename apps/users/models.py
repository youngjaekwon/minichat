from __future__ import annotations

import hashlib
from io import BytesIO

from django.contrib.auth import authenticate
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.files.base import ContentFile
from django.db import models

import structlog
from PIL import Image

from apps.users.constants import (
    PROFILE_IMAGE_ALLOWED_FORMATS,
    PROFILE_IMAGE_MAX_PIXELS,
    PROFILE_IMAGE_MAX_SIZE,
)


class CustomUserManager(BaseUserManager["User"]):
    """이메일 기반 사용자 생성을 위한 커스텀 매니저."""

    def get_by_email(self, email: str) -> User | None:
        """이메일로 사용자를 조회한다."""
        try:
            return self.get(email__iexact=email)
        except self.model.DoesNotExist:
            return None

    def get_by_id(self, user_id: int) -> User | None:
        """ID로 사용자를 조회한다."""
        try:
            return self.get(pk=user_id)
        except self.model.DoesNotExist:
            return None

    def _validate_image(self, image_file) -> Image.Image:
        """이미지 파일을 검증한다.

        Raises:
            ValueError: 유효하지 않은 이미지인 경우.
        """
        try:
            img: Image.Image = Image.open(image_file)

            # 지원하는 포맷인지 확인
            if img.format not in PROFILE_IMAGE_ALLOWED_FORMATS:
                raise ValueError(
                    f"지원하지 않는 이미지 형식입니다. "
                    f"허용: {', '.join(PROFILE_IMAGE_ALLOWED_FORMATS)}"
                )

            # 이미지 크기 검증 (decompression bomb 방지)
            if img.width * img.height > PROFILE_IMAGE_MAX_PIXELS:
                raise ValueError(
                    f"이미지가 너무 큽니다. (최대 {PROFILE_IMAGE_MAX_PIXELS // 1_000_000}MP)"
                )

            # 실제 이미지인지 확인 (verify 후 다시 열어야 함)
            img.verify()
            image_file.seek(0)
            img = Image.open(image_file)

        except OSError as e:
            raise ValueError("유효하지 않은 이미지 파일입니다.") from e

        return img

    def _resize_profile_image(
        self, image_file, max_size: tuple[int, int] = PROFILE_IMAGE_MAX_SIZE
    ) -> ContentFile:
        """프로필 이미지를 검증하고 리사이징한다."""
        img = self._validate_image(image_file)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        original_name = getattr(image_file, "name", "profile.jpg")
        name_without_ext = original_name.rsplit(".", 1)[0]
        new_name = f"{name_without_ext}.jpg"

        return ContentFile(buffer.read(), name=new_name)

    def create_user(
        self,
        email: str,
        password: str | None = None,
        profile_image=None,
        **extra_fields,
    ) -> User:
        """새로운 사용자 인스턴스를 생성한다.

        프로필 이미지 리사이징을 포함한다.

        Args:
            email: 사용자 이메일.
            password: 비밀번호.
            profile_image: 프로필 이미지 파일.
            **extra_fields: 추가 필드.
        """
        if not email:
            raise ValueError("이메일은 필수입니다.")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)

        if profile_image:
            profile_image = self._resize_profile_image(profile_image)

        user = self.model(
            email=email, profile_image=profile_image or "", **extra_fields
        )
        user.set_password(password)

        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields,
    ) -> User:
        """슈퍼유저를 생성하고 저장한다.

        Django createsuperuser 명령어에서 사용된다.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("슈퍼유저는 is_staff=True여야 합니다.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("슈퍼유저는 is_superuser=True여야 합니다.")

        user = self.create_user(email, password, **extra_fields)
        user.save(using=self._db)
        return user


def user_profile_image_path(instance: User, filename: str) -> str:
    """프로필 이미지 저장 경로를 생성한다.

    새 사용자 생성 시 pk가 None일 수 있으므로 이메일 해시를 사용한다.
    """
    email_hash = hashlib.sha256(instance.email.lower().encode()).hexdigest()[:16]
    return f"profile_images/{email_hash}/{filename}"


class User(AbstractBaseUser, PermissionsMixin):
    """이메일 기반 커스텀 유저 모델."""

    email = models.EmailField(
        "이메일",
        unique=True,
        error_messages={
            "unique": "이미 사용 중인 이메일입니다.",
        },
    )
    name = models.CharField("이름", max_length=100)
    profile_image = models.ImageField(
        "프로필 사진",
        upload_to=user_profile_image_path,
        blank=True,
    )
    job_title = models.CharField("직업/소속", max_length=100, blank=True)
    is_active = models.BooleanField("활성화", default=True)
    is_staff = models.BooleanField("스태프 권한", default=False)
    date_joined = models.DateTimeField("가입일", auto_now_add=True)

    objects: CustomUserManager = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자"

    def __str__(self) -> str:
        return self.email

    @classmethod
    def authenticate_user(
        cls,
        email: str,
        password: str,
    ) -> User | None:
        """사용자 인증을 수행한다."""
        user = authenticate(username=email, password=password)
        if user is not None and user.is_active:
            structlog.contextvars.bind_contextvars(
                action="user_login",
                success=True,
                user_id=user.pk,
            )
            return user

        structlog.contextvars.bind_contextvars(
            action="user_login",
            success=False,
            failure_reason="invalid_credentials",
        )
        return None
