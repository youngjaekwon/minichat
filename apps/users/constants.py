# 프로필 이미지 설정
PROFILE_IMAGE_MAX_SIZE = (300, 300)  # 리사이징 최대 크기 (width, height)
PROFILE_IMAGE_MAX_PIXELS = 10_000_000  # 10MP 제한 (decompression bomb 방지)
PROFILE_IMAGE_ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
PROFILE_IMAGE_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB 파일 크기 제한
