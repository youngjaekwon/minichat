# Change: 대화방 기본 기능 추가

## Why

minichat 애플리케이션의 핵심 기능인 대화방을 구현한다. 사용자들이 1:1 대화 및 그룹 대화를 생성하고, 메시지를 주고받을 수 있는 기본적인 채팅 기능을 제공해야 한다.

## What Changes

- Room 모델 생성 (1:1 및 그룹 대화 지원)
- Message 모델 생성 (메시지 저장)
- 대화 목록 페이지 (참여 대화방, 마지막 메시지 미리보기)
- 대화 상세 페이지 (메시지 목록, 상대방 프로필)
- 메시지 전송 기능 (Form POST, 페이지 새로고침 방식)
- 새 대화 시작 기능 (상대방 선택)

**참고**: 이 단계에서는 WebSocket 실시간 통신 및 읽음/안읽음 상태 추적을 구현하지 않는다.

## Impact

- Affected specs: 신규 `chat-room`, `chat-views` 스펙 생성
- Affected code: `apps/chat/` 앱 신규 생성, `config/urls.py` URL 추가
- Dependencies: `user-auth` 스펙 (로그인 사용자만 대화 기능 사용 가능)
