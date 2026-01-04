# realtime-sidebar Specification

## Purpose
TBD - created by archiving change add-message-read-status. Update Purpose after archive.
## Requirements
### Requirement: Sidebar Channel Group

시스템은 사용자별 사이드바 업데이트를 위한 Channel Group을 제공해야 한다(SHALL).

- 그룹 이름 형식: `user_chat_rooms_{user_id}`
- WebSocket 연결 시 자동 참가
- WebSocket 연결 해제 시 자동 퇴장

#### Scenario: 사이드바 그룹 참가

- **WHEN** 사용자가 채팅 페이지에 WebSocket 연결하면
- **THEN** `user_chat_rooms_{user_id}` 그룹에 자동 참가해야 한다

#### Scenario: 사이드바 그룹 퇴장

- **WHEN** WebSocket 연결이 종료되면
- **THEN** `user_chat_rooms_{user_id}` 그룹에서 자동 퇴장해야 한다

### Requirement: Sidebar Update Broadcast

시스템은 새 메시지 수신 시 사이드바 업데이트를 브로드캐스트해야 한다(SHALL).

#### Scenario: 새 메시지 시 사이드바 업데이트

- **WHEN** 대화방에 새 메시지가 전송되면
- **THEN** 해당 방의 모든 참여자에게 사이드바 업데이트가 전송되어야 한다
- **AND** 업데이트에는 room_id, 최신 메시지 미리보기, 안읽은 수, updated_at이 포함되어야 한다

#### Scenario: 읽음 상태 변경 시 사이드바 업데이트

- **WHEN** 사용자가 대화방의 메시지를 읽으면
- **THEN** 해당 사용자에게 사이드바 업데이트가 전송되어야 한다
- **AND** 해당 방의 안읽은 메시지 수가 0으로 표시되어야 한다

### Requirement: Sidebar Realtime Reordering

시스템은 새 메시지 수신 시 사이드바의 채팅방 순서를 실시간으로 변경해야 한다(SHALL).

#### Scenario: 새 메시지로 채팅방 순서 변경

- **WHEN** 새 메시지를 수신하면
- **THEN** 해당 채팅방이 사이드바 최상단으로 이동해야 한다
- **AND** 페이지 새로고침 없이 실시간으로 반영되어야 한다

#### Scenario: 검색 중 순서 유지

- **WHEN** 사이드바에서 채팅방을 검색 중일 때 새 메시지를 수신하면
- **THEN** 채팅방 순서가 변경되지 않아야 한다
- **AND** 안읽은 메시지 배지는 업데이트되어야 한다

### Requirement: Sidebar Message Preview Update

시스템은 새 메시지 수신 시 사이드바의 메시지 미리보기를 실시간 업데이트해야 한다(SHALL).

#### Scenario: 미리보기 텍스트 업데이트

- **WHEN** 새 메시지를 수신하면
- **THEN** 해당 채팅방의 미리보기 텍스트가 새 메시지 내용으로 업데이트되어야 한다
- **AND** 50자를 초과하면 말줄임표(...)로 잘려야 한다

#### Scenario: 미리보기 시간 업데이트

- **WHEN** 새 메시지를 수신하면
- **THEN** 해당 채팅방의 시간 표시가 새 메시지의 시간으로 업데이트되어야 한다

### Requirement: Unread Badge Display

시스템은 각 채팅방에 안읽은 메시지 수 배지를 표시해야 한다(SHALL).

#### Scenario: 안읽은 메시지 배지 표시

- **WHEN** 채팅방에 안읽은 메시지가 있으면
- **THEN** 해당 채팅방 항목에 안읽은 수를 나타내는 배지가 표시되어야 한다
- **AND** 배지는 빨간색 원형이어야 한다

#### Scenario: 배지 숫자 제한

- **WHEN** 안읽은 메시지가 99개를 초과하면
- **THEN** 배지에 "99+"로 표시되어야 한다

#### Scenario: 배지 숨김

- **WHEN** 채팅방의 모든 메시지를 읽으면
- **THEN** 해당 채팅방의 배지가 숨겨져야 한다

#### Scenario: 현재 선택된 채팅방 배지

- **WHEN** 현재 보고 있는 채팅방에 새 메시지가 오면
- **THEN** 해당 채팅방의 배지가 표시되지 않아야 한다 (이미 읽음 처리됨)

