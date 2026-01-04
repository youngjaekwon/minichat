# Change: 메시지 읽음 상태 추적 및 실시간 사이드바 갱신

## Why

사용자가 메시지를 읽었는지 확인할 수 없어 소통 효율이 낮다. 또한 사이드바가 새 메시지 수신 시 실시간으로 갱신되지 않아 사용자가 페이지를 새로고침해야 최신 상태를 확인할 수 있다.

## What Changes

### 1. 메시지 읽음 상태 추적
- MessageRead 모델 추가 (메시지-사용자 간 읽음 기록)
- 대화방 입장 시 해당 방의 모든 메시지를 읽음 처리
- 1:1/그룹 채팅 모두 안읽은 인원 수를 숫자로 표시 (카카오톡 방식)

### 2. 채팅창 읽음 표시 UI
- 내 메시지 옆에 안읽은 인원 수 표시 (예: "1")
- 실시간으로 읽음 상태 업데이트 (상대방이 읽으면 숫자 감소/제거)

### 3. 사이드바 실시간 갱신
- 새 메시지 수신 시 해당 채팅방의 미리보기 텍스트 실시간 업데이트
- 각 채팅방별 안읽은 메시지 수 배지 표시
- 새 메시지 수신 시 채팅방 순서 변경 (최신 메시지가 있는 방이 위로)
- 단, 검색 중일 때는 순서 유지

### 4. WebSocket 확장
- 읽음 상태 변경 시 브로드캐스트
- 사이드바 갱신을 위한 별도 WebSocket 채널 (선택적)

## Impact

- Affected specs:
  - `message-read` (신규): 읽음 상태 모델 및 비즈니스 로직
  - `realtime-sidebar` (신규): 사이드바 실시간 갱신
  - `realtime-chat`: 읽음 상태 WebSocket 메시지 추가
  - `chat-views`: 읽음 표시 UI, 사이드바 배지

- Affected code:
  - `apps/chat/models.py`: MessageRead 모델 추가
  - `apps/chat/consumers.py`: 읽음 상태 브로드캐스트
  - `apps/chat/views.py`: 읽음 처리 로직
  - `templates/chat/room.html`: 읽음 표시 UI, 사이드바 갱신
  - `static/js/chat/`: 사이드바 WebSocket 로직

- Database: MessageRead 테이블 추가 (마이그레이션 필요)
