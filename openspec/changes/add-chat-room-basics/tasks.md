# Tasks: 대화방 기본 기능

## 1. 프로젝트 구조 설정

- [ ] 1.1 `apps/chat/` Django 앱 생성
- [ ] 1.2 `config/settings/base.py`에 앱 등록
- [ ] 1.3 `config/urls.py`에 chat URL 추가

## 2. 모델 구현

- [ ] 2.1 Room 모델 생성 (name, participants, is_direct, created_by, timestamps)
- [ ] 2.2 Message 모델 생성 (room, sender, content, created_at)
- [ ] 2.3 RoomManager 구현 (get_by_user, get_or_create_direct, create_group)
- [ ] 2.4 MessageManager 구현 (get_by_room, create_message)
- [ ] 2.5 마이그레이션 생성 및 적용

## 3. 모델 테스트

- [ ] 3.1 Room 모델 테스트 (생성, 참여자 추가)
- [ ] 3.2 Message 모델 테스트 (생성, 빈 메시지 검증)
- [ ] 3.3 RoomManager 테스트 (get_by_user, get_or_create_direct, create_group)
- [ ] 3.4 MessageManager 테스트 (get_by_room, create_message)
- [ ] 3.5 RoomFactory, MessageFactory 추가

## 4. 뷰 및 URL 구현

- [ ] 4.1 대화 목록 뷰 (`/chat/`)
- [ ] 4.2 대화 상세 뷰 (`/chat/<room_id>/`)
- [ ] 4.3 메시지 전송 뷰 (`/chat/<room_id>/send/`)
- [ ] 4.4 새 대화 시작 뷰 (`/chat/new/`)
- [ ] 4.5 MessageForm 작성

## 5. 뷰 테스트

- [ ] 5.1 대화 목록 뷰 테스트 (인증, 목록 표시)
- [ ] 5.2 대화 상세 뷰 테스트 (인증, 권한 검증, 메시지 표시)
- [ ] 5.3 메시지 전송 뷰 테스트 (성공, 빈 메시지, 권한)
- [ ] 5.4 새 대화 시작 뷰 테스트 (검색, 대화방 생성/조회)

## 6. 템플릿 구현

- [ ] 6.1 대화 목록 템플릿 (`chat/room_list.html`)
- [ ] 6.2 대화 상세 템플릿 (`chat/room_detail.html`)
- [ ] 6.3 새 대화 시작 템플릿 (`chat/new_conversation.html`)

## 7. 최종 검증

- [ ] 7.1 전체 테스트 실행 (`uv run pytest`)
- [ ] 7.2 수동 기능 테스트
