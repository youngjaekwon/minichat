"""
Django dev settings for minichat project.

Docker 개발 환경용 설정.
"""

from .local import *  # noqa: F401, F403, E402

# Docker 환경에서 Debug Toolbar 지원
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "debug_toolbar.middleware.show_toolbar_with_docker",
}
