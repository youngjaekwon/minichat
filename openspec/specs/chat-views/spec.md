# chat-views Specification

## Purpose
TBD - created by archiving change add-chat-room-basics. Update Purpose after archive.
## Requirements
### Requirement: Chat Authentication

모든 채팅 관련 페이지는 로그인된 사용자만 접근할 수 있어야 한다(SHALL).

#### Scenario: 비로그인 사용자 접근 시도

- **WHEN** 비로그인 사용자가 채팅 페이지에 접근하면
- **THEN** 로그인 페이지로 리다이렉트되어야 한다

#### Scenario: 로그인 사용자 접근

- **WHEN** 로그인된 사용자가 채팅 페이지에 접근하면
- **THEN** 정상적으로 페이지가 표시되어야 한다

### Requirement: Room List Page

시스템은 사용자가 참여 중인 대화 목록을 표시하는 페이지를 제공해야 한다(SHALL).

- URL: `/chat/`
- 대화 목록을 최근 업데이트 순으로 표시
- 각 대화 항목에 표시: 대화 상대/이름, 마지막 메시지 미리보기, 시간/날짜
- 1:1 대화: 상대방 이름으로 표시
- 그룹 대화: 대화방 이름으로 표시

#### Scenario: 대화 목록 조회

- **WHEN** 로그인 사용자가 `/chat/`에 접근하면
- **THEN** 참여 중인 대화 목록이 표시되어야 한다
- **AND** 최근 업데이트 순으로 정렬되어야 한다

#### Scenario: 대화가 없는 경우

- **WHEN** 참여 중인 대화가 없는 사용자가 목록에 접근하면
- **THEN** 빈 상태 안내 메시지가 표시되어야 한다

#### Scenario: 마지막 메시지 미리보기

- **WHEN** 대화 목록이 표시될 때
- **THEN** 각 대화의 마지막 메시지가 50자 이내로 표시되어야 한다

#### Scenario: 시간/날짜 표시

- **WHEN** 대화 목록이 표시될 때
- **THEN** 오늘 메시지는 시간만, 이전 메시지는 날짜로 표시되어야 한다

### Requirement: Room Detail Page

시스템은 대화방의 메시지 목록과 입력 폼을 표시하는 페이지를 제공해야 한다(SHALL).

- URL: `/chat/<room_id>/`
- 상대방/대화방 정보 표시 (이름, 직함)
- 메시지 목록 (시간순)
- 날짜별 구분선
- 메시지 입력 폼

#### Scenario: 대화 상세 조회

- **WHEN** 참여자가 대화방 상세 페이지에 접근하면
- **THEN** 해당 대화방의 메시지 목록이 표시되어야 한다
- **AND** 메시지가 시간순으로 정렬되어야 한다

#### Scenario: 비참여자 접근 차단

- **WHEN** 대화방에 참여하지 않은 사용자가 접근하면
- **THEN** 403 Forbidden 응답이 반환되어야 한다

#### Scenario: 상대방 프로필 표시

- **WHEN** 1:1 대화방 상세 페이지를 조회하면
- **THEN** 상대방의 이름과 직함이 표시되어야 한다

#### Scenario: 날짜 구분선 표시

- **WHEN** 다른 날짜의 메시지들이 있을 때
- **THEN** 날짜별로 구분선이 표시되어야 한다

### Requirement: Send Message

시스템은 대화방에서 메시지를 전송하는 기능을 제공해야 한다(SHALL).

- URL: `/chat/<room_id>/send/` (POST only)
- Form POST 방식으로 메시지 전송
- 전송 후 대화 상세 페이지로 리다이렉트

#### Scenario: 메시지 전송 성공

- **WHEN** 참여자가 유효한 내용으로 메시지를 전송하면
- **THEN** 메시지가 저장되어야 한다
- **AND** 대화 상세 페이지로 리다이렉트되어야 한다

#### Scenario: 빈 메시지 전송 시도

- **WHEN** 빈 내용으로 메시지를 전송하려고 하면
- **THEN** 메시지가 저장되지 않아야 한다
- **AND** 대화 상세 페이지로 리다이렉트되어야 한다

#### Scenario: 비참여자 전송 시도

- **WHEN** 대화방에 참여하지 않은 사용자가 메시지를 전송하려고 하면
- **THEN** 403 Forbidden 응답이 반환되어야 한다

### Requirement: New Conversation Page

시스템은 새 대화를 시작할 수 있는 페이지를 제공해야 한다(SHALL).

- URL: `/chat/new/`
- 대화 상대 검색/선택 기능
- 선택 후 대화방 생성 및 이동

#### Scenario: 새 1:1 대화 시작

- **WHEN** 사용자가 대화 상대를 선택하고 대화를 시작하면
- **THEN** 기존 1:1 대화방이 있으면 해당 대화방으로 이동해야 한다
- **AND** 없으면 새 대화방을 생성하고 이동해야 한다

#### Scenario: 사용자 검색

- **WHEN** 사용자 이름 또는 이메일로 검색하면
- **THEN** 일치하는 사용자 목록이 표시되어야 한다
- **AND** 자기 자신은 검색 결과에서 제외되어야 한다

