# minichat

Python 3.13 + Django 기반 실시간 채팅 애플리케이션

## 주요 기능

### 사용자 인증
- 이메일 기반 회원가입/로그인

### 채팅
- 1:1 대화 및 그룹 대화방
- WebSocket 기반 실시간 메시지 전송/수신
- 연결 끊김 시 자동 재연결 및 메시지 동기화
- 메시지 전송 확인 (ACK)
- 사이드바 실시간 업데이트 (새 메시지 미리보기, 채팅방 순서 변경)

### 읽음 추적
- 메시지별 읽음 상태 추적
- 안읽은 메시지 수 표시
- 실시간 읽음 알림 (WebSocket)

### 검색
- 대화방 내 메시지 검색 (pg_trgm + GIN 인덱스)
- 사이드바에서 전체 대화 검색
- 검색 결과 네비게이션 및 키워드 하이라이트

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
