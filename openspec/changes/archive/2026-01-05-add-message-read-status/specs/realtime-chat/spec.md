## MODIFIED Requirements

### Requirement: ChatConsumer

시스템은 WebSocket 연결을 처리하는 ChatConsumer를 제공해야 한다(SHALL).

- AsyncWebsocketConsumer 기반 구현
- URL 패턴: `ws/chat/<room_id>/`
- 인증된 사용자만 연결 허용
- 대화방 참여자만 연결 허용
- AuthMiddlewareStack을 통한 세션 기반 인증
- **연결 시 사용자별 사이드바 그룹(`user_chat_rooms_{user_id}`)에 자동 참가**
- **연결 시 해당 방의 안읽은 메시지 자동 읽음 처리**

#### Scenario: WebSocket 연결 성공

- **WHEN** 인증된 사용자가 참여 중인 대화방에 WebSocket 연결을 시도하면
- **THEN** 연결이 수락되어야 한다
- **AND** 해당 대화방의 Channel Layer 그룹에 참가해야 한다
- **AND** `user_chat_rooms_{user_id}` 그룹에 참가해야 한다
- **AND** 해당 방의 안읽은 메시지가 읽음 처리되어야 한다
- **AND** 발신자들에게 읽음 상태 변경이 알려져야 한다

#### Scenario: 비인증 사용자 연결 거부

- **WHEN** 비인증 사용자가 WebSocket 연결을 시도하면
- **THEN** 연결이 거부되어야 한다 (close code 4001)

#### Scenario: 비참여자 연결 거부

- **WHEN** 대화방에 참여하지 않은 사용자가 WebSocket 연결을 시도하면
- **THEN** 연결이 거부되어야 한다 (close code 4003)

#### Scenario: 존재하지 않는 대화방 연결 시도

- **WHEN** 존재하지 않는 대화방 ID로 WebSocket 연결을 시도하면
- **THEN** 연결이 거부되어야 한다 (close code 4004)

#### Scenario: 연결 해제

- **WHEN** WebSocket 연결이 종료되면
- **THEN** Channel Layer 그룹에서 퇴장해야 한다
- **AND** `user_chat_rooms_{user_id}` 그룹에서 퇴장해야 한다

### Requirement: Realtime Message Send

시스템은 WebSocket을 통해 실시간 메시지 전송 기능을 제공해야 한다(SHALL).

- JSON 형식으로 메시지 수신
- 메시지 내용 유효성 검사
- 데이터베이스에 메시지 저장
- 대화방 참여자 전원에게 브로드캐스트
- client_id 기반 전송 확인 (ACK) 응답
- **참여자 전원에게 사이드바 업데이트 브로드캐스트**

#### Scenario: 메시지 전송 성공

- **WHEN** 참여자가 유효한 메시지를 WebSocket으로 전송하면
- **THEN** 메시지가 데이터베이스에 저장되어야 한다
- **AND** 대화방 참여자 전원에게 메시지가 브로드캐스트되어야 한다
- **AND** 발신자에게 message_ack 응답이 전송되어야 한다
- **AND** 참여자 전원의 `user_chat_rooms_{user_id}` 그룹에 사이드바 업데이트가 전송되어야 한다

#### Scenario: 빈 메시지 전송 시도

- **WHEN** 빈 내용으로 메시지를 전송하려고 하면
- **THEN** 메시지가 저장되지 않아야 한다
- **AND** 에러 응답이 전송되어야 한다 (code: EMPTY_MESSAGE)

#### Scenario: 잘못된 JSON 형식 전송

- **WHEN** 잘못된 JSON 형식으로 메시지를 전송하면
- **THEN** 에러 응답이 전송되어야 한다 (code: INVALID_FORMAT)

### Requirement: Realtime Message Receive

시스템은 WebSocket을 통해 실시간 메시지 수신 기능을 제공해야 한다(SHALL).

- Channel Layer 그룹 메시지 수신
- JSON 형식으로 클라이언트에 전달
- 메시지 정보 포함: id, content, sender_id, sender_name, created_at, **unread_count**

#### Scenario: 메시지 수신

- **WHEN** 같은 대화방의 다른 참여자가 메시지를 전송하면
- **THEN** 해당 메시지가 실시간으로 수신되어야 한다
- **AND** 메시지 정보가 JSON 형식으로 전달되어야 한다
- **AND** unread_count(안읽은 인원 수)가 포함되어야 한다

## ADDED Requirements

### Requirement: Read Status Broadcast

시스템은 읽음 상태 변경을 WebSocket으로 브로드캐스트해야 한다(SHALL).

#### Scenario: 읽음 상태 브로드캐스트

- **WHEN** 사용자가 대화방에 입장하여 메시지를 읽으면
- **THEN** 해당 메시지의 발신자에게 `read_status` 메시지가 전송되어야 한다
- **AND** 메시지에는 message_ids와 각 메시지의 새로운 unread_count가 포함되어야 한다

#### Scenario: 읽음 상태 메시지 형식

- **WHEN** 읽음 상태 변경 메시지가 전송되면
- **THEN** 메시지 타입은 `read_status`이어야 한다
- **AND** `message_reads` 배열에 {message_id, unread_count} 객체가 포함되어야 한다
