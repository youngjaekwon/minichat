# Project Context

## Purpose

minichat - Python 3.13 기반 실시간 채팅 애플리케이션. Django와 Channels를 사용하여 WebSocket 기반 실시간 통신을 구현한다.

## Tech Stack

**Backend**
- Python 3.13, Django 5.x, Django Channels 4.x
- Daphne 4.x (ASGI Server)
- Celery 5.x (Task Queue)

**Database & Cache**
- PostgreSQL 16 (GIN Index, Full-text Search)
- Redis 7.x (Channels Layer, 캐시, Celery Broker)

**Frontend**
- Django Templates (서버 사이드 렌더링)
- Alpine.js 3.x, HTMX 1.x
- Tailwind CSS 3.x

**Infrastructure**
- Docker, Railway, GitHub Actions
- django-structlog (Structured Logging)
- django-anymail (이메일)

**Package Manager**
- uv (pyproject.toml, dependency-groups)

## Project Conventions

### Code Style

**포매팅**: Black(88자), isort, flake8, pre-commit 훅으로 자동 검사

**명명 규칙**:
- 변수/함수: snake_case
- 클래스: PascalCase
- 상수: UPPER_SNAKE_CASE
- 모델 필드: 소문자 snake_case

**Import 순서**: future → standard library → third-party → Django → local (각 그룹 내 알파벳순)

**모델 구조**: 필드 → class Meta → `__str__` → save() → get_absolute_url() → 커스텀 메서드

**뷰/템플릿**: 첫 매개변수는 `request`, 템플릿 태그는 `{{ var }}`, `{% tag %}` 형식

### Architecture Patterns

Fat Model + Thin View 패턴을 사용하여 비즈니스 로직을 Model 레이어에 집중한다.

**Model 레이어**: 모든 비즈니스 로직 배치
- Custom Manager: 조회(get_by_*) 및 생성(create_*) 로직
- Model 메서드: 인스턴스 관련 비즈니스 로직 (예: User.login())
- Private 메서드: 보조 기능 (_resize_image 등)

**Form 레이어**: 유효성 검사 담당, ModelForm의 save()에서 Model Manager 호출

**View 레이어 (Thin View)**: HTTP 요청/응답 처리만 담당, 비즈니스 로직 직접 구현 금지

### Testing Strategy

**TDD (Red-Green-Refactor)**:
1. Red: 실패하는 테스트 먼저 작성
2. Green: 테스트 통과하는 최소 코드 작성
3. Refactor: 테스트 통과 유지하며 코드 정리

**도구**: pytest, pytest-django, factory-boy, coverage

**명령어**:
- 전체: `uv run pytest`
- 특정: `uv run pytest tests/test_users.py::test_user_create`
- 커버리지: `uv run coverage run -m pytest && uv run coverage report`

### Git Workflow

**커밋 메시지 형식**: 타이틀은 영어, 설명(body)은 한글

**포맷**: `<type>: <subject>`

**Type**: feat, fix, docs, style, refactor, perf, test, chore, revert

**예시**:
```
feat: add user service

유저 서비스 추가
```

## Domain Context

실시간 채팅 애플리케이션으로, 사용자 간 1:1 및 그룹 채팅을 지원한다. WebSocket을 통한 실시간 메시지 전송과 PostgreSQL FTS를 활용한 메시지 검색 기능을 제공한다.

## Important Constraints

**Logging**: [Stripe Canonical Log Lines](https://stripe.com/blog/canonical-log-lines) 패턴 적용. 요청당 하나의 압축된 로그 라인을 발행하여 빠른 쿼리와 집계를 가능하게 한다.

**포함 필드**: request_id, http_method, http_path, http_status, user_id, duration, database_queries, error_info

**환경별 출력**:
- 개발: ConsoleRenderer (가독성)
- 프로덕션: JSONRenderer (로그 수집기 파싱용)

## External Dependencies

- **PostgreSQL 16**: 메인 데이터베이스, Full-text Search
- **Redis 7.x**: Channels Layer, 세션, 캐시, Celery Broker
- **SendGrid/Mailgun**: 이메일 발송 (django-anymail)
- **Railway**: 배포 플랫폼
- **GitHub Actions**: CI/CD
