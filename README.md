# minichat

Python 3.13 + Django 기반 실시간 채팅 애플리케이션

## 주요 기능

- 1:1 채팅 및 그룹 채팅
- WebSocket 기반 실시간 메시지 전송
- 메시지 검색 (PostgreSQL Full-text Search)
- 읽음 상태 추적

## 기술 스택

| 영역          | 기술                        |
| ------------- | --------------------------- |
| Backend       | Django 5.1, Django Channels |
| Database      | PostgreSQL                  |
| Cache/Channel | Redis                       |
| Task Queue    | Celery                      |
| ASGI Server   | Uvicorn                     |

## 시작하기

```bash
# 의존성 설치
uv sync --group dev

# 마이그레이션
uv run python manage.py migrate

# 개발 서버 실행
uv run python manage.py runserver
```

## 환경 설정

`envs/env.example`을 참고하여 `envs/env.local` 파일 생성

## 테스트

```bash
uv run pytest
```

## 배포

Docker + Railway 사용
