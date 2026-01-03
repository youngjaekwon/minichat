"""
Celery 설정 모듈

이메일 발송 등 비동기 작업을 처리한다.
"""

import os

from celery import Celery

# Django settings 모듈 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("minichat")

# Django settings에서 CELERY_ 접두사를 가진 설정을 로드
app.config_from_object("django.conf:settings", namespace="CELERY")

# 등록된 Django 앱에서 tasks.py 자동 검색
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """디버그용 태스크"""
    print(f"Request: {self.request!r}")
