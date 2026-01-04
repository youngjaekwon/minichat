"""
config 패키지 초기화

Celery 앱을 Django와 함께 로드한다.
"""

from config.celery import app as celery_app

__all__ = ("celery_app",)
