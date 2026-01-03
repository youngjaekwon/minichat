## ADDED Requirements

### Requirement: Room Model

시스템은 대화방 정보를 저장하는 Room 모델을 제공해야 한다(SHALL).

- `name`: 대화방 이름 (최대 100자, 빈 값 허용 - 그룹 대화용)
- `participants`: 참여자 목록 (User M:N 관계)
- `participant_count`: 참여자 수 (PositiveSmallIntegerField, 기본값 0, M2M 변경 시 자동 갱신)
- `is_direct`: 1:1 대화 여부 (Boolean, 기본값 True)
- `direct_chat_key`: 1:1 대화 고유 키 (unique, nullable - 그룹 대화는 null, 동시성 처리용)
- `created_by`: 대화방 생성자 (User ForeignKey)
- `created_at`: 생성 일시
- `updated_at`: 수정 일시 (메시지 전송 시 갱신)

#### Scenario: 1:1 대화방 생성

- **WHEN** 두 명의 참여자로 is_direct=True인 대화방을 생성하면
- **THEN** 새로운 Room 인스턴스가 생성되어야 한다
- **AND** 생성자가 자동으로 참여자에 추가되어야 한다

#### Scenario: 그룹 대화방 생성

- **WHEN** 이름과 여러 참여자로 is_direct=False인 대화방을 생성하면
- **THEN** name 필드가 설정된 대화방이 생성되어야 한다
- **AND** 모든 지정된 참여자가 추가되어야 한다

#### Scenario: 대화방 참여자 추가

- **WHEN** 기존 대화방에 새 참여자를 추가하면
- **THEN** 해당 사용자가 participants에 추가되어야 한다

### Requirement: Message Model

시스템은 메시지 정보를 저장하는 Message 모델을 제공해야 한다(SHALL).

- `room`: 소속 대화방 (Room ForeignKey)
- `sender`: 발신자 (User ForeignKey)
- `content`: 메시지 내용 (TextField)
- `created_at`: 전송 일시

#### Scenario: 메시지 생성

- **WHEN** 유효한 대화방, 발신자, 내용으로 메시지를 생성하면
- **THEN** 새로운 Message 인스턴스가 생성되어야 한다
- **AND** 대화방의 updated_at이 갱신되어야 한다

#### Scenario: 빈 메시지 전송 방지

- **WHEN** 빈 내용으로 메시지를 생성하려고 하면
- **THEN** 유효성 검사 오류가 발생해야 한다

### Requirement: Room Manager

시스템은 대화방 조회 및 생성을 위한 RoomManager를 제공해야 한다(SHALL).

#### Scenario: 사용자별 대화방 조회

- **WHEN** `get_by_user(user)` 메서드를 호출하면
- **THEN** 해당 사용자가 참여 중인 모든 대화방이 반환되어야 한다
- **AND** 최근 업데이트 순으로 정렬되어야 한다

#### Scenario: 1:1 대화방 조회 또는 생성

- **WHEN** `get_or_create_direct(user1, user2)` 메서드를 호출하면
- **THEN** 두 사용자 간 기존 1:1 대화방이 있으면 반환해야 한다
- **AND** 없으면 새로 생성하여 반환해야 한다

#### Scenario: 그룹 대화방 생성

- **WHEN** `create_group(name, created_by, participants)` 메서드를 호출하면
- **THEN** is_direct=False인 새 대화방이 생성되어야 한다
- **AND** 생성자와 지정된 참여자들이 모두 participants에 추가되어야 한다

### Requirement: Message Manager

시스템은 메시지 조회 및 생성을 위한 MessageManager를 제공해야 한다(SHALL).

#### Scenario: 대화방별 메시지 조회

- **WHEN** `get_by_room(room)` 메서드를 호출하면
- **THEN** 해당 대화방의 모든 메시지가 반환되어야 한다
- **AND** 생성 시간 오름차순으로 정렬되어야 한다

#### Scenario: 메시지 생성

- **WHEN** `create_message(room, sender, content)` 메서드를 호출하면
- **THEN** 새 메시지가 생성되어야 한다
- **AND** 대화방의 updated_at이 갱신되어야 한다
