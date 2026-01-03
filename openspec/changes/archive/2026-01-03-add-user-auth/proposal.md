# Change: 커스텀 유저 모델 및 이메일 기반 인증 구현

## Why

minichat 채팅 앱의 핵심 기능인 사용자 관리와 인증 시스템이 필요하다. 사용자는 이름, 프로필 사진, 직업 정보를 가지며, 이메일을 통해 회원가입하고 로그인할 수 있어야 한다.

## What Changes

- 커스텀 User 모델 생성 (`apps/users`)
  - 이메일을 로그인 식별자로 사용
  - 이름, 프로필 사진, 직업 필드 추가
- 회원가입 기능
  - 이메일, 비밀번호, 이름 입력으로 계정 생성
  - 이메일 중복 검증
- 로그인/로그아웃 기능
  - Django 세션 기반 인증
  - 이메일과 비밀번호로 인증

## Impact

- Affected specs: `user-auth` (신규)
- Affected code:
  - `apps/users/` - 새 앱 생성
  - `config/settings/base.py` - AUTH_USER_MODEL 설정
  - `templates/` - 인증 관련 템플릿
