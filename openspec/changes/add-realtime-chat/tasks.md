# Tasks

## 1. ASGI 설정 및 인프라

- [ ] 1.1 `config/asgi.py`에 AuthMiddlewareStack 추가
- [ ] 1.2 `config/settings/base.py` Redis Channel Layer 설정 최적화 (capacity, expiry, group_expiry)
- [ ] 1.3 `apps/chat/routing.py` 생성 - WebSocket URL 패턴 정의

## 2. ChatConsumer 구현

- [ ] 2.1 `apps/chat/consumers.py` 생성
- [ ] 2.2 AsyncWebsocketConsumer 기반 ChatConsumer 클래스 작성
- [ ] 2.3 connect() - 인증 확인, Room 존재 여부 확인, 참여자 검증, Channel Layer 그룹 참가
- [ ] 2.4 disconnect() - Channel Layer 그룹 퇴장
- [ ] 2.5 receive() - 메시지 수신, 유효성 검사, DB 저장, 그룹 브로드캐스트, ACK 응답
- [ ] 2.6 chat_message() - Channel Layer에서 메시지 수신 후 클라이언트 전송
- [ ] 2.7 에러 응답 헬퍼 메서드 (EMPTY_MESSAGE, INVALID_FORMAT, RATE_LIMITED)

## 3. 메시지 동기화

- [ ] 3.1 WebSocket URL에 last_message_id 쿼리 파라미터 지원
- [ ] 3.2 connect()에서 누락 메시지 조회 및 순차 전송 로직

## 4. Rate Limiting

- [ ] 4.1 Redis 기반 sliding window counter 구현
- [ ] 4.2 분당 60개, 초당 5개 제한 적용
- [ ] 4.3 제한 초과 시 에러 응답 + 재시도 대기 시간 안내

## 5. Heartbeat

- [ ] 5.1 서버 측 30초 ping 전송 로직 (asyncio task)
- [ ] 5.2 클라이언트 pong 응답 처리
- [ ] 5.3 10초 타임아웃 시 연결 종료

## 6. 프론트엔드 WebSocket 연동

- [ ] 6.1 Alpine.js 컴포넌트로 WebSocket 클라이언트 구현
- [ ] 6.2 연결 상태 관리 (연결 중, 연결됨, 재연결 중, 연결 끊김)
- [ ] 6.3 Exponential Backoff 재연결 로직 (초기 1초, 최대 30초, 계수 2, jitter)
- [ ] 6.4 재연결 시 last_message_id 파라미터 전송
- [ ] 6.5 메시지 전송 핸들러 (client_id UUID 생성)
- [ ] 6.6 message_ack 처리 (전송 중 → 전송 완료 상태)
- [ ] 6.7 메시지 수신 및 DOM 업데이트
- [ ] 6.8 자동 스크롤 (새 메시지 수신 시)
- [ ] 6.9 Heartbeat pong 응답 처리

## 7. 테스트 작성

- [ ] 7.1 ChatConsumer 단위 테스트 (channels.testing.WebsocketCommunicator)
- [ ] 7.2 인증/권한 테스트 (비인증 4001, 비참여자 4003, 대화방 없음 4004)
- [ ] 7.3 메시지 송수신 통합 테스트
- [ ] 7.4 Rate Limiting 테스트
- [ ] 7.5 메시지 동기화 테스트 (last_message_id)
- [ ] 7.6 Heartbeat 테스트
