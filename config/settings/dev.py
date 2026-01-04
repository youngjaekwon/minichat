"""
Django dev settings for minichat project.

Docker 개발 환경용 설정.
"""

from .local import *  # noqa: F401, F403, E402

# WhiteNoise: 개발 환경에서 collectstatic 없이 정적 파일 서빙
WHITENOISE_USE_FINDERS = True
