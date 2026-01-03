# Tasks: add-user-auth

## 1. 커스텀 User 모델

- [x] 1.1 `apps/users/` 앱 생성 (models.py, services.py, selectors.py, urls.py, admin.py)
- [x] 1.2 커스텀 User 모델 정의 (email, name, profile_image, job_title 필드)
- [x] 1.3 CustomUserManager 구현 (create_user, create_superuser)
- [x] 1.4 `config/settings/base.py`에 AUTH_USER_MODEL 설정
- [x] 1.5 마이그레이션 생성 및 적용
- [x] 1.6 Admin 등록

## 2. 프로필 이미지 리사이징

- [x] 2.1 Pillow 의존성 추가
- [x] 2.2 `profile_image_resize` 서비스 함수 작성 (Celery 마이그레이션 대비 독립적 구현)
- [x] 2.3 User 모델 save 시 리사이징 호출 (동기 처리)

## 3. 회원가입 기능

- [x] 3.1 `user_create` 서비스 함수 작성
- [x] 3.2 회원가입 뷰 및 템플릿 구현
- [x] 3.3 이메일 중복 검증 로직

## 4. 로그인/로그아웃 기능

- [x] 4.1 `user_login` 서비스 함수 작성
- [x] 4.2 로그인 뷰 및 템플릿 구현
- [x] 4.3 로그아웃 뷰 구현
- [x] 4.4 로그인 성공/실패 시 리다이렉트 설정

## 5. 테스트

- [x] 5.1 UserFactory 생성
- [x] 5.2 User 모델 테스트
- [x] 5.3 서비스 함수 테스트 (user_create, user_login, profile_image_resize)
- [x] 5.4 뷰 테스트 (회원가입, 로그인, 로그아웃)
