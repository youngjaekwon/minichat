# message-read Specification

## Purpose
TBD - created by archiving change add-message-read-status. Update Purpose after archive.
## Requirements
### Requirement: MessageRead Model

시스템은 메시지 읽음 상태를 추적하는 MessageRead 모델을 제공해야 한다(SHALL).

- `message`: 메시지 (Message ForeignKey)
- `user`: 읽은 사용자 (User ForeignKey)
- `read_at`: 읽은 시간 (DateTimeField, auto_now_add)
- unique_together: ['message', 'user']
- 인덱스: (message, user), (user, read_at)

#### Scenario: 읽음 기록 생성

- **WHEN** 사용자가 메시지를 읽으면
- **THEN** 해당 메시지와 사용자에 대한 MessageRead 레코드가 생성되어야 한다
- **AND** read_at에 현재 시간이 기록되어야 한다

#### Scenario: 중복 읽음 방지

- **WHEN** 이미 읽은 메시지를 다시 읽으면
- **THEN** 새로운 레코드가 생성되지 않아야 한다
- **AND** 기존 레코드가 유지되어야 한다

### Requirement: MessageRead Manager

시스템은 읽음 상태 관리를 위한 MessageReadManager를 제공해야 한다(SHALL).

#### Scenario: 대화방 메시지 일괄 읽음 처리

- **WHEN** `mark_as_read(room, user)` 메서드를 호출하면
- **THEN** 해당 방에서 사용자가 읽지 않은 모든 메시지가 읽음 처리되어야 한다
- **AND** 자신이 보낸 메시지는 제외되어야 한다
- **AND** 읽음 처리된 메시지 ID 목록이 반환되어야 한다

#### Scenario: 안읽은 메시지 수 조회

- **WHEN** `get_unread_count(room, user)` 메서드를 호출하면
- **THEN** 해당 방에서 사용자가 읽지 않은 메시지 수가 반환되어야 한다
- **AND** 자신이 보낸 메시지는 제외되어야 한다

#### Scenario: 사용자의 전체 안읽은 메시지 수 조회

- **WHEN** `get_total_unread_count(user)` 메서드를 호출하면
- **THEN** 모든 참여 대화방의 안읽은 메시지 총 수가 반환되어야 한다

### Requirement: Message Unread Count

시스템은 메시지별 안읽은 인원 수를 조회하는 기능을 제공해야 한다(SHALL).

#### Scenario: 안읽은 인원 수 조회

- **WHEN** 메시지 목록을 `with_unread_count()` QuerySet 메서드로 조회하면
- **THEN** 각 메시지에 `unread_count` 속성이 포함되어야 한다
- **AND** unread_count는 (참여자 수 - 읽은 인원 수 - 1(발신자)) 값이어야 한다

#### Scenario: 모든 참여자가 읽은 경우

- **WHEN** 메시지를 모든 참여자가 읽었으면
- **THEN** unread_count가 0이어야 한다

### Requirement: Read Status Notification

시스템은 읽음 상태 변경 시 발신자에게 알림을 제공해야 한다(SHALL).

#### Scenario: 읽음 알림 전송

- **WHEN** 수신자가 메시지를 읽으면
- **THEN** 발신자에게 WebSocket으로 읽음 상태 변경이 알려져야 한다
- **AND** 알림에는 메시지 ID와 새로운 unread_count가 포함되어야 한다

#### Scenario: 일괄 읽음 알림

- **WHEN** 대화방 입장 시 여러 메시지가 일괄 읽음 처리되면
- **THEN** 각 발신자에게 해당 메시지들의 읽음 상태가 알려져야 한다

