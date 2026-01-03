# user-auth Specification

## Purpose
TBD - created by archiving change add-user-auth. Update Purpose after archive.
## Requirements
### Requirement: Custom User Model

시스템은 이메일 기반의 커스텀 User 모델을 제공해야 한다(SHALL).

- email: 고유한 이메일 주소 (로그인 식별자)
- name: 사용자 이름 (필수)
- profile_image: 프로필 사진 (선택)
- job_title: 직업/소속 (선택)
- is_active: 계정 활성화 여부
- date_joined: 가입 일시

#### Scenario: 커스텀 유저 모델 사용

- **WHEN** AUTH_USER_MODEL이 설정되면
- **THEN** 커스텀 User 모델이 인증에 사용되어야 한다

#### Scenario: 이메일 고유성 보장

- **WHEN** 이미 존재하는 이메일로 유저 생성을 시도하면
- **THEN** 중복 오류가 발생해야 한다

### Requirement: Profile Image Resize

시스템은 프로필 이미지 업로드 시 리사이징을 수행해야 한다(SHALL).

- 리사이징 로직은 별도 서비스 함수(`profile_image_resize`)로 분리하여 추후 Celery task로 마이그레이션 가능하도록 한다
- 초기 구현은 업로드 시점에 동기적으로 처리한다

#### Scenario: 프로필 이미지 업로드 시 리사이징

- **WHEN** 사용자가 프로필 이미지를 업로드하면
- **THEN** 이미지가 지정된 크기로 리사이징되어야 한다
- **AND** 리사이징된 이미지가 저장되어야 한다

#### Scenario: 리사이징 로직 분리

- **WHEN** 프로필 이미지 리사이징이 필요하면
- **THEN** `profile_image_resize` 서비스 함수가 호출되어야 한다
- **AND** 해당 함수는 독립적으로 Celery task로 전환 가능해야 한다

### Requirement: User Registration

시스템은 이메일 기반 회원가입 기능을 제공해야 한다(SHALL).

#### Scenario: 회원가입 성공

- **WHEN** 유효한 이메일, 비밀번호, 이름을 입력하면
- **THEN** 새로운 사용자 계정이 생성되어야 한다
- **AND** 사용자는 자동으로 로그인 상태가 되어야 한다

#### Scenario: 중복 이메일로 회원가입 시도

- **WHEN** 이미 등록된 이메일로 회원가입을 시도하면
- **THEN** 오류 메시지가 표시되어야 한다
- **AND** 계정이 생성되지 않아야 한다

#### Scenario: 약한 비밀번호로 회원가입 시도

- **WHEN** Django 비밀번호 정책을 만족하지 않는 비밀번호로 회원가입을 시도하면
- **THEN** 비밀번호 정책 위반 오류가 표시되어야 한다

### Requirement: User Login

시스템은 이메일과 비밀번호를 통한 로그인 기능을 제공해야 한다(SHALL).

#### Scenario: 로그인 성공

- **WHEN** 유효한 이메일과 비밀번호를 입력하면
- **THEN** 사용자가 인증되어야 한다
- **AND** 세션이 생성되어야 한다
- **AND** 홈 페이지로 리다이렉트되어야 한다

#### Scenario: 잘못된 비밀번호로 로그인 시도

- **WHEN** 올바른 이메일과 잘못된 비밀번호를 입력하면
- **THEN** 오류 메시지가 표시되어야 한다
- **AND** 로그인되지 않아야 한다

#### Scenario: 존재하지 않는 이메일로 로그인 시도

- **WHEN** 등록되지 않은 이메일로 로그인을 시도하면
- **THEN** 오류 메시지가 표시되어야 한다
- **AND** 로그인되지 않아야 한다

### Requirement: User Logout

시스템은 로그아웃 기능을 제공해야 한다(SHALL).

#### Scenario: 로그아웃 성공

- **WHEN** 로그인된 사용자가 로그아웃을 요청하면
- **THEN** 세션이 종료되어야 한다
- **AND** 로그인 페이지로 리다이렉트되어야 한다

