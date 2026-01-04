# Tasks

## 1. ASGI 설정 및 인프라

- [x] 1.1 `config/asgi.py`에 AuthMiddlewareStack 추가
- [x] 1.2 `config/settings/base.py` Redis Channel Layer 설정 최적화 (capacity, expiry, group_expiry)
- [x] 1.3 `apps/chat/routing.py` 생성 - WebSocket URL 패턴 정의

## 2. ChatConsumer 구현

- [x] 2.1 `apps/chat/consumers.py` 생성
- [x] 2.2 AsyncWebsocketConsumer 기반 ChatConsumer 클래스 작성
- [x] 2.3 connect() - 인증 확인, Room 존재 여부 확인, 참여자 검증, Channel Layer 그룹 참가
- [x] 2.4 disconnect() - Channel Layer 그룹 퇴장
- [x] 2.5 receive() - 메시지 수신, 유효성 검사, DB 저장, 그룹 브로드캐스트, ACK 응답
- [x] 2.6 chat_message() - Channel Layer에서 메시지 수신 후 클라이언트 전송
- [x] 2.7 에러 응답 헬퍼 메서드 (EMPTY_MESSAGE, INVALID_FORMAT)

## 3. 메시지 동기화

- [x] 3.1 WebSocket URL에 last_message_id 쿼리 파라미터 지원
- [x] 3.2 connect()에서 누락 메시지 조회 및 순차 전송 로직

## 4. 프론트엔드 WebSocket 연동

- [x] 4.1 Alpine.js 컴포넌트로 WebSocket 클라이언트 구현
- [x] 4.2 연결 상태 관리 (연결 중, 연결됨, 재연결 중, 연결 끊김)
- [x] 4.3 Exponential Backoff 재연결 로직 (초기 1초, 최대 30초, 계수 2, jitter)
- [x] 4.4 재연결 시 last_message_id 파라미터 전송
- [x] 4.5 메시지 전송 핸들러 (client_id UUID 생성)
- [x] 4.6 message_ack 처리 (전송 중 → 전송 완료 상태)
- [x] 4.7 메시지 수신 및 DOM 업데이트
- [x] 4.8 자동 스크롤 (새 메시지 수신 시)

## 5. 테스트 작성

- [x] 5.1 ChatConsumer 단위 테스트 (channels.testing.WebsocketCommunicator)
- [x] 5.2 인증/권한 테스트 (비인증 4001, 비참여자 4003, 대화방 없음 4004)
- [x] 5.3 메시지 송수신 통합 테스트
- [x] 5.4 메시지 동기화 테스트 (last_message_id)
