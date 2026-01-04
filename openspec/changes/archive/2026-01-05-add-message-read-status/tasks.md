## 1. Backend - MessageRead 모델

- [x] 1.1 MessageRead 모델 정의 (`apps/chat/models.py`)
  - message, user, read_at 필드
  - unique_together 제약조건
  - 인덱스 추가
- [x] 1.2 MessageReadManager 구현
  - `mark_as_read(room, user)`: 방의 안읽은 메시지 일괄 읽음 처리
  - `get_unread_count(room, user)`: 사용자의 해당 방 안읽은 메시지 수
- [x] 1.3 MessageQuerySet 확장
  - `with_unread_count()`: 메시지별 안읽은 인원 수 annotate
- [x] 1.4 마이그레이션 생성 및 테스트
- [x] 1.5 MessageRead 모델 단위 테스트

## 2. Backend - WebSocket 및 Celery Task

- [x] 2.1 WebSocket 메시지 타입 추가 (`apps/chat/messages.py`)
  - `ReadStatusMessage`: 읽음 상태 변경 알림
  - `SidebarUpdateMessage`: 사이드바 갱신 알림
- [x] 2.2 Celery task 구현 (`apps/chat/tasks.py`)
  - `broadcast_sidebar_update`: 사이드바 업데이트 비동기 브로드캐스트
  - `save_read_status`: 읽음 상태 DB 저장 (비동기)
- [x] 2.3 ChatConsumer 읽음 처리 (`apps/chat/consumers.py`)
  - 연결 시 안읽은 메시지 일괄 읽음 처리
  - 채팅방 그룹에 즉시 읽음 상태 브로드캐스트
- [x] 2.4 사용자별 사이드바 Channel Group 관리
  - `user_chat_rooms_{user_id}` 그룹 추가
  - 연결/해제 시 그룹 참가/퇴장
- [x] 2.5 새 메시지 시 사이드바 업데이트 브로드캐스트
  - Celery task로 참여자 전원에게 `sidebar_update` 메시지 전송
- [x] 2.6 WebSocket 및 Celery 통합 테스트

## 3. Backend - API

- [x] 3.1 채팅방 목록 API 확장 (`apps/chat/views.py`)
  - 각 방의 안읽은 메시지 수 포함
- [x] 3.2 메시지 목록 API 확장
  - 각 메시지의 안읽은 인원 수 포함
- [x] 3.3 API 테스트

## 4. Frontend - 채팅창 읽음 표시

- [x] 4.1 메시지 컴포넌트 수정 (`templates/chat/room.html`)
  - 내 메시지 옆에 안읽은 인원 수 표시 UI
  - 조건: unread_count > 0일 때만 표시
- [x] 4.2 Alpine.js 데이터 모델 확장 (`static/js/chat/`)
  - 메시지 객체에 unread_count 속성 추가
  - `read_status` WebSocket 메시지 핸들러
- [x] 4.3 실시간 읽음 상태 업데이트
  - 상대방이 읽으면 해당 메시지의 unread_count 감소

## 5. Frontend - 사이드바 실시간 갱신

- [x] 5.1 사이드바 컴포넌트 수정 (`templates/chat/room.html`)
  - 채팅방별 안읽은 메시지 수 배지 UI
  - 미리보기 텍스트 동적 업데이트 영역
- [x] 5.2 Alpine.js 사이드바 상태 관리
  - `sidebar_update` WebSocket 메시지 핸들러
  - `handleSidebarUpdate`, `updateSidebarDOM` 메서드
- [x] 5.3 채팅방 순서 동적 변경
  - 새 메시지 수신 시 해당 방 최상단 이동
  - 검색 모드 시 순서 유지 (sidebar-search-input 체크)
- [x] 5.4 배지 UI 스타일링
  - 빨간 원형 배지, 숫자 99+ 처리
