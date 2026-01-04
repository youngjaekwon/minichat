# Change: Add Realtime Chat via WebSocket

## Why

현재 채팅 시스템은 Form POST 방식으로 메시지를 전송하고 페이지를 새로고침해야 새 메시지를 확인할 수 있다. 사용자 경험 향상을 위해 WebSocket 기반 실시간 메시지 송수신 기능이 필요하다.

## What Changes

**핵심 기능**:
- ChatConsumer 구현 (Django Channels AsyncWebsocketConsumer)
- WebSocket 라우팅 설정 (ws/chat/<room_id>/)
- 실시간 메시지 송수신 (Channel Layer 그룹 활용)
- Alpine.js 기반 프론트엔드 WebSocket 연동

**확장성 및 안정성**:
- AuthMiddlewareStack 적용 (세션 기반 인증)
- Rate Limiting (분당 60개, 초당 5개 제한)
- Heartbeat ping-pong (30초 주기, 10초 타임아웃)
- Exponential Backoff 재연결 (최대 10회, jitter 포함)
- 재연결 시 메시지 동기화 (last_message_id 기반)
- Redis Channel Layer 설정 최적화

**UI/UX**:
- 메시지 전송 확인 (ACK 기반)
- 자동 스크롤

## Impact

- Affected specs: `realtime-chat` (신규 capability, 8개 요구사항)
- Affected code:
  - `apps/chat/consumers.py` (신규)
  - `apps/chat/routing.py` (신규)
  - `config/asgi.py` (수정 - AuthMiddlewareStack 추가)
  - `config/settings/base.py` (수정 - Channel Layer 설정 최적화)
  - `templates/chat/room.html` (수정 - Alpine.js WebSocket 클라이언트)
