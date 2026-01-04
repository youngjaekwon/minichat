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
│       ├── models.py           # 데이터 모델 + 비즈니스 로직 (Fat Model)
│       ├── forms.py            # 폼 (ModelForm + save() 메서드)
│       ├── views.py            # 뷰 (Thin View - HTTP 처리만)
│       ├── apis.py             # API 엔드포인트
│       ├── serializers.py      # 입출력 직렬화
│       ├── urls.py
│       ├── admin.py
│       └── tests/
│           ├── __init__.py
│           ├── test_models.py
│           ├── test_forms.py
│           ├── test_views.py
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

### 타입 힌트

Python 3.10+ Union 문법을 사용한다:

- `User | None` (O) vs `Optional[User]` (X)
- `str | None` (O) vs `Optional[str]` (X)
- Manager에 제네릭 타입 힌트 적용: `BaseUserManager[User]`

### 명명 규칙

- 변수/함수: snake_case
- 클래스: PascalCase
- 상수: UPPER_SNAKE_CASE
- 모델 필드: 소문자 snake_case

### Import 순서

future → standard library → third-party → Django → local 순서로 정렬한다. 각 그룹 내에서는 알파벳순으로 정렬한다.

### 모델 구조

필드 정의 → objects Manager → USERNAME_FIELD(인증 모델) → class Meta → `__str__` → save() → get_absolute_url() → 클래스 메서드 → 인스턴스 메서드 순서로 작성한다.

### 상수 관리

앱별 `constants.py` 파일에 매직 숫자와 설정값을 정의한다.

### 뷰/템플릿

뷰 함수의 첫 매개변수는 반드시 `request`로 명명한다. 템플릿 태그는 중괄호 안에 공백을 포함한다 (예: `{{ var }}`, `{% tag %}`).

## 아키텍처 패턴

Fat Model + Thin View 패턴을 사용하여 비즈니스 로직을 Model 레이어에 집중한다.

### Model 레이어

모든 비즈니스 로직은 Model 레이어에 배치한다:

- **Custom QuerySet**: 체이닝 가능한 필터 로직을 QuerySet 메서드로 구현한다
- **Custom Manager**: 조회(get_by\_\*) 및 생성(create\_\*) 로직을 Manager 메서드로 구현한다
- **Model 메서드**: 인스턴스 관련 비즈니스 로직은 Model의 클래스/인스턴스 메서드로 구현한다
- **Private 메서드**: 보조 기능은 Manager의 private 메서드(\_resize_image)로 구현한다

#### QuerySet과 Manager 구분

- **QuerySet 메서드**: "테이블 전체"에 대한 필터링/정렬 로직. 체이닝이 필요한 경우 반드시 QuerySet에 정의한다
- **Manager 메서드**: 단일 객체 조회(get_by\_\*) 또는 생성(create\_\*) 로직. QuerySet을 반환하지 않는 경우 Manager에 정의한다
- **Model 인스턴스 메서드**: "행(row) 수준" 로직. 특정 인스턴스에 대한 연산을 수행한다

#### Custom QuerySet 패턴

체이닝 가능한 쿼리 메서드는 Custom QuerySet에 정의하고 `as_manager()`로 Manager를 생성한다:

- QuerySet 메서드는 반드시 QuerySet을 반환하여 체이닝을 보장한다
- 고급 사용 시 `Manager.from_queryset()`으로 Manager와 QuerySet을 결합한다
- QuerySet 메서드는 테스트, Django Admin, Generic View 등 어디서든 일관되게 사용할 수 있다

#### QuerySet 메서드 명명 규칙

- **필터 메서드**: 상태나 조건을 나타내는 형용사/명사형 사용
  - `active()`, `published()`, `for_user(user)`, `created_after(date)`
- **정렬 메서드**: `ordered_by_*` 형식 사용
  - `ordered_by_created()`, `ordered_by_popularity()`

#### Manager 메서드 명명 규칙

- **Selector 메서드** (조회): `get_by_*` - None을 반환하여 안전한 조회 지원
  - `get_by_email(email)` → `User | None`
  - `get_by_id(user_id)` → `User | None`
- **Creator 메서드** (생성): `create_*` - 객체 생성 및 관련 처리 수행
  - `create_user(email, password, **kwargs)` → `User`

#### Fat Model 주의사항

Fat Model 패턴의 과도한 적용은 모델 비대화를 초래한다. 다음 원칙을 준수한다:

- 복잡한 비즈니스 로직이 여러 모델에 걸쳐 있으면 별도 서비스 모듈(utils.py)로 분리를 고려한다
- Model 메서드는 해당 인스턴스의 데이터만 다루도록 한다
- 외부 API 호출 등 인프라 의존성은 Model에서 분리한다

### Form 레이어

- ModelForm의 save() 메서드에서 Model Manager를 호출하여 객체를 생성한다
- 유효성 검사만 담당하고, 복잡한 비즈니스 로직은 Model로 위임한다

### View 레이어 (Thin View)

- HTTP 요청/응답 처리만 담당한다
- `form.is_valid()` → `form.save()` 또는 Model 메서드 호출
- 비즈니스 로직 직접 구현 금지
- 클래스 기반 뷰(CBV)를 기본으로 사용한다

### CBV (Class-Based Views) 가이드라인

SSR(Server Side Rendering) 환경에서 Django Generic CBV를 적극 활용한다.

#### CBV vs FBV 선택 기준

- **CBV 사용**: CRUD 작업, 반복적인 패턴, 코드 재사용이 필요한 경우
- **FBV 사용**: 단순한 일회성 로직, CBV로 표현하기 복잡한 특수 케이스

권장 접근법: Generic CBV로 시작하고, 필요시 일반 CBV로 전환, 정말 필요한 경우에만 FBV를 사용한다.

#### 주요 Generic CBV와 용도

- **ListView**: 모델 목록 표시 (페이지네이션 내장)
- **DetailView**: 단일 객체 상세 표시
- **CreateView**: 객체 생성 폼 처리
- **UpdateView**: 객체 수정 폼 처리
- **DeleteView**: 객체 삭제 확인 및 처리
- **FormView**: 일반 폼 처리 (모델과 무관)
- **TemplateView**: 단순 템플릿 렌더링

#### Mixin 순서 (MRO)

Mixin은 반드시 왼쪽에서 오른쪽 순서로 상속하며, View 클래스보다 먼저 선언한다:

1. CsrfExemptMixin (사용 시 가장 왼쪽)
2. LoginRequiredMixin
3. PermissionRequiredMixin
4. 기타 커스텀 Mixin
5. Generic View (ListView, CreateView 등)

#### 주요 오버라이드 메서드

- **get_queryset()**: 목록 조회 시 QuerySet 커스터마이징. 단순한 경우 `queryset` 클래스 속성 사용
- **get_context_data()**: 템플릿에 전달할 추가 컨텍스트 데이터. 반드시 `super().get_context_data(**kwargs)` 호출
- **form_valid()**: 폼 검증 성공 시 추가 처리. 단순한 경우 `success_url` 클래스 속성 사용
- **get_object()**: DetailView/UpdateView/DeleteView에서 객체 조회 커스터마이징
- **dispatch()**: 뷰 실행 전 권한 검사 등 전처리

#### 인증/권한 Mixin

- **LoginRequiredMixin**: 로그인 필수 뷰에 적용
- **PermissionRequiredMixin**: 특정 권한 필요 시 적용. `permission_required` 속성으로 권한 지정
- **UserPassesTestMixin**: 커스텀 조건 검사 시 `test_func()` 메서드 오버라이드

인증 Mixin은 권한 Mixin보다 먼저 배치한다. 인증되지 않은 사용자의 권한을 검사하는 것은 무의미하다.

#### django-braces 활용

추가적인 Mixin 기능이 필요한 경우 django-braces 패키지를 활용한다:

- **FormValidMessageMixin**: 폼 성공 시 메시지 표시
- **SetHeadlineMixin**: 템플릿에 headline 컨텍스트 전달
- **SelectRelatedMixin**: select_related 자동 적용
- **PrefetchRelatedMixin**: prefetch_related 자동 적용

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
