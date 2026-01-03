<!-- OPENSPEC:START -->

# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

minichat - Python 3.13 기반 채팅 애플리케이션 프로젝트

## 개발 환경

- Python 3.13
- 패키지 관리: uv (pyproject.toml)

## 주요 명령어

```bash
# 의존성 설치
uv sync

# 애플리케이션 실행
uv run python main.py

# 의존성 추가
uv add <package-name>
```

## 프로젝트 구조

```
project/
├── pyproject.toml              # 의존성 및 프로젝트 설정 (uv)
├── uv.lock                     # 의존성 락 파일 (자동 생성)
├── .python-version             # Python 버전 지정
├── .pre-commit-config.yaml     # pre-commit 훅 설정
├── manage.py
│
├── config/                     # 프로젝트 설정
│   ├── __init__.py             # Celery 앱 등록
│   ├── celery.py               # Celery 설정
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py             # 공통 설정
│   │   ├── local.py            # 개발 환경
│   │   ├── production.py       # 프로덕션 환경
│   │   └── test.py             # 테스트 환경
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── envs/                       # 환경 변수 파일
│   ├── env.example             # 예제 (Git 포함)
│   ├── env.local               # 개발 환경 (Git 제외)
│   └── env.production          # 프로덕션 환경 (Git 제외)
│
├── apps/                       # Django 앱들
│   └── <app_name>/
│       ├── __init__.py
│       ├── models.py           # 데이터 모델만
│       ├── services.py         # 쓰기 비즈니스 로직
│       ├── selectors.py        # 읽기 비즈니스 로직
│       ├── apis.py             # API 엔드포인트
│       ├── serializers.py      # 입출력 직렬화
│       ├── urls.py
│       ├── admin.py
│       └── tests/
│           ├── __init__.py
│           ├── test_services.py
│           ├── test_selectors.py
│           └── test_apis.py
│
├── templates/                  # 전역 템플릿
├── static/                     # 전역 정적 파일
└── tests/                      # 통합 테스트
    ├── conftest.py             # pytest 공용 픽스처
    └── factories.py            # factory-boy 팩토리
```

### uv 의존성 그룹

pyproject.toml에서 의존성을 그룹으로 관리한다:

- 기본 의존성: `[project.dependencies]`
- 개발 의존성: `[dependency-groups.dev]` (pytest, factory-boy, coverage 등)
- 프로덕션 의존성: `[dependency-groups.prod]` (gunicorn, whitenoise 등)

환경별 설치 명령:

- 개발: `uv sync --group dev`
- 프로덕션: `uv sync --group prod`
- 전체: `uv sync --all-groups`

## 기술 스택

| 영역                | 기술             | 버전 | 선택 이유                   |
| ------------------- | ---------------- | ---- | --------------------------- |
| Framework           | Django           | 5.x  | 요구사항, 검증된 생산성     |
| 실시간 통신         | Django Channels  | 4.x  | Django 통합 WebSocket       |
| ASGI Server         | Daphne           | 4.x  | Channels 공식 권장          |
| Database            | PostgreSQL       | 16   | GIN Index, Full-text Search |
| 검색                | PostgreSQL FTS   | -    | GIN Index + SearchVector    |
| Cache/Channel Layer | Redis            | 7.x  | Channels Layer, 세션, 캐시  |
| Task Queue          | Celery           | 5.x  | 이메일 비동기 발송          |
| Message Broker      | Redis            | 7.x  | Celery Broker 겸용          |
| Frontend            | Django Templates | -    | 서버 사이드 렌더링          |
| Frontend 상호작용   | Alpine.js        | 3.x  | 경량 반응형 UI              |
| Frontend 부분 갱신  | HTMX             | 1.x  | AJAX 간소화                 |
| CSS                 | Tailwind CSS     | 3.x  | 빠른 반응형 UI 구현         |
| 컨테이너            | Docker           | -    | 개발/배포 환경 일관성       |
| 배포                | Railway          | -    | Git push 배포, Redis 지원   |
| CI/CD               | GitHub Actions   | -    | 자동 테스트/배포            |
| 이메일              | Django-anymail   | -    | SendGrid/Mailgun 연동       |

## Django 코딩 컨벤션

### 코드 포매팅

Ruff를 사용하며 pre-commit 훅으로 자동 검사한다. 타입 체크는 Pyright를 사용한다.

### 명명 규칙

- 변수/함수: snake_case
- 클래스: PascalCase
- 상수: UPPER_SNAKE_CASE
- 모델 필드: 소문자 snake_case

### Import 순서

future → standard library → third-party → Django → local 순서로 정렬한다. 각 그룹 내에서는 알파벳순으로 정렬한다.

### 모델 구조

필드 정의 → class Meta → `__str__` → save() → get_absolute_url() → 커스텀 메서드 순서로 작성한다.

### 뷰/템플릿

뷰 함수의 첫 매개변수는 반드시 `request`로 명명한다. 템플릿 태그는 중괄호 안에 공백을 포함한다 (예: `{{ var }}`, `{% tag %}`).

## 아키텍처 패턴

[HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide) 기반으로 비즈니스 로직을 분리한다.

### 서비스 레이어

쓰기 작업(생성, 수정, 삭제)을 담당하는 함수들을 `services.py`에 배치한다. 네이밍은 `<entity>_<action>` 패턴을 따른다 (예: user_create, order_cancel).

### 셀렉터

읽기 작업(조회, 필터링)을 담당하는 함수들을 `selectors.py`에 배치한다. 네이밍은 `<entity>_list`, `<entity>_get` 패턴을 따른다.

### 비즈니스 로직 배치 금지 영역

views, serializers, forms, model.save(), signals, custom managers/querysets에는 비즈니스 로직을 작성하지 않는다.

## TDD (테스트 주도 개발)

### 테스트 도구

pytest, pytest-django, factory-boy, coverage를 사용한다.

### 테스트 명령어

- 전체 테스트: `uv run pytest`
- 특정 테스트: `uv run pytest tests/test_users.py::test_user_create`
- 커버리지: `uv run coverage run -m pytest && uv run coverage report`

### Red-Green-Refactor 사이클

1. Red: 실패하는 테스트를 먼저 작성한다
2. Green: 테스트를 통과하는 최소한의 코드를 작성한다
3. Refactor: 테스트가 통과하는 상태를 유지하면서 코드를 정리한다

### Factory 패턴

테스트 데이터 생성에는 factory-boy를 사용한다. 팩토리 클래스는 `tests/factories.py`에 정의한다.

## Structured Logging

[django-structlog](https://django-structlog.readthedocs.io/)을 사용하여 구조화된 로깅을 구현한다.

### 설정

MIDDLEWARE에 `django_structlog.middlewares.RequestMiddleware`를 추가하고, INSTALLED_APPS에 `django_structlog`을 등록한다.

### 환경별 출력

- 개발: ConsoleRenderer를 사용하여 컬러풀하고 가독성 높은 출력
- 프로덕션: JSONRenderer를 사용하여 로그 수집기가 파싱하기 쉬운 형식

### Canonical Log Lines

[Stripe의 Canonical Log Lines](https://stripe.com/blog/canonical-log-lines) 패턴을 적용한다.

**개념**: 요청당 하나의 압축된 로그 라인을 요청 완료 시점에 발행하여, 해당 요청의 모든 핵심 정보를 한곳에 모은다. 이를 "canonical"이라 부르는 이유는 해당 요청에 대한 권위 있는 단일 소스이기 때문이다.

**장점**:

- 분산된 로그를 조합할 필요 없이 단일 라인으로 빠른 쿼리와 집계 가능
- 장애 발생 시 첫 번째 조사 시작점으로 활용
- 이상치 식별 및 실패 요청의 공통 특성 파악 용이

**포함 필드**:

- 요청 식별: request_id, service, release
- HTTP 정보: http_method, http_path, http_status
- 인증 정보: user_id, auth_type, api_key_id
- 성능 지표: duration, database_queries, db_duration
- 비즈니스 메트릭: rate_limit_remaining, permissions_used
- 에러 정보: error_id, error_class, error_message (실패 시)

**구현 방식**: 미들웨어 기반으로 요청 생명주기 동안 컨텍스트에 정보를 누적하고, 요청 완료(또는 예외 발생) 시점에 단일 로그로 발행한다. django-structlog의 RequestMiddleware가 이 패턴을 지원한다.

**활용 사례**:

- HTTP 500 에러를 예외 클래스별로 그룹화하여 원인 분석
- 특정 엔드포인트의 느린 쿼리 패턴 식별
- 사용자별 API 사용량 및 Rate Limit 현황 모니터링

**주의사항**: Canonical Log Lines는 고수준 정보를 제공하므로, 상세한 디버깅이 필요한 경우 전통적인 로그와 병행하여 사용한다.

## Git Commits

### 커밋 메시지 형식

- 타이틀: 영어로 작성
- 설명(body): 한글로 작성

### 커밋 메시지 포맷

```
<type>: <subject>

<body>
```

### Type 종류

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포매팅, 세미콜론 누락 등 (코드 변경 없음)
- `refactor`: 리팩토링 (기능 변경 없음)
- `perf`: 성능 개선
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 파일 등 기타 변경
- `revert`: 이전 커밋 되돌리기

### 예시

```
feat: add user service

유저 서비스 추가
```
