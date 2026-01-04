## ADDED Requirements

### Requirement: ChatConsumer

시스템은 WebSocket 연결을 처리하는 ChatConsumer를 제공해야 한다(SHALL).

- AsyncWebsocketConsumer 기반 구현
- URL 패턴: `ws/chat/<room_id>/`
- 인증된 사용자만 연결 허용
- 대화방 참여자만 연결 허용
- AuthMiddlewareStack을 통한 세션 기반 인증

#### Scenario: WebSocket 연결 성공

- **WHEN** 인증된 사용자가 참여 중인 대화방에 WebSocket 연결을 시도하면
- **THEN** 연결이 수락되어야 한다
- **AND** 해당 대화방의 Channel Layer 그룹에 참가해야 한다

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

### Requirement: Realtime Message Send

시스템은 WebSocket을 통해 실시간 메시지 전송 기능을 제공해야 한다(SHALL).

- JSON 형식으로 메시지 수신
- 메시지 내용 유효성 검사
- 데이터베이스에 메시지 저장
- 대화방 참여자 전원에게 브로드캐스트
- client_id 기반 전송 확인 (ACK) 응답

#### Scenario: 메시지 전송 성공

- **WHEN** 참여자가 유효한 메시지를 WebSocket으로 전송하면
- **THEN** 메시지가 데이터베이스에 저장되어야 한다
- **AND** 대화방 참여자 전원에게 메시지가 브로드캐스트되어야 한다
- **AND** 발신자에게 message_ack 응답이 전송되어야 한다

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
- 메시지 정보 포함: id, content, sender_id, sender_name, created_at

#### Scenario: 메시지 수신

- **WHEN** 같은 대화방의 다른 참여자가 메시지를 전송하면
- **THEN** 해당 메시지가 실시간으로 수신되어야 한다
- **AND** 메시지 정보가 JSON 형식으로 전달되어야 한다

### Requirement: Message Synchronization

시스템은 재연결 시 누락된 메시지를 동기화해야 한다(SHALL).

- 클라이언트가 마지막 수신 메시지 ID를 쿼리 파라미터로 전송
- 서버는 해당 ID 이후의 메시지를 조회하여 순차 전송

#### Scenario: 재연결 시 메시지 동기화

- **WHEN** WebSocket이 재연결되고 last_message_id 파라미터가 포함되면
- **THEN** 해당 ID 이후의 메시지를 조회해야 한다
- **AND** 누락된 메시지를 시간순으로 클라이언트에 전달해야 한다

#### Scenario: 초기 연결 (last_message_id 없음)

- **WHEN** last_message_id 없이 WebSocket 연결이 수립되면
- **THEN** 과거 메시지를 전송하지 않아야 한다
- **AND** 이후 수신되는 메시지만 전달해야 한다

### Requirement: Frontend WebSocket Integration

시스템은 Alpine.js 기반 WebSocket 클라이언트를 제공해야 한다(SHALL).

- WebSocket 연결 관리 (연결, 재연결, 종료)
- 메시지 전송 핸들러 (client_id 생성 포함)
- 메시지 수신 및 DOM 업데이트
- 자동 스크롤 (새 메시지 수신 시)

#### Scenario: WebSocket 연결 및 메시지 전송

- **WHEN** 대화방 상세 페이지에 접근하면
- **THEN** WebSocket 연결이 자동으로 수립되어야 한다
- **AND** 메시지 입력 후 전송 시 WebSocket으로 전송되어야 한다

#### Scenario: 실시간 메시지 표시

- **WHEN** WebSocket으로 새 메시지가 수신되면
- **THEN** 페이지 새로고침 없이 메시지 목록에 추가되어야 한다
- **AND** 메시지 영역이 자동 스크롤되어야 한다

#### Scenario: 연결 재수립 (Exponential Backoff)

- **WHEN** WebSocket 연결이 끊어지면
- **THEN** 자동으로 재연결을 시도해야 한다
- **AND** 초기 1초, 최대 30초, 계수 2의 지수 백오프를 적용해야 한다
- **AND** 최대 10회까지 재시도해야 한다

#### Scenario: 메시지 전송 확인

- **WHEN** 메시지를 전송하면
- **THEN** 전송 중 상태가 표시되어야 한다
- **AND** message_ack 수신 시 전송 완료 상태로 변경되어야 한다
