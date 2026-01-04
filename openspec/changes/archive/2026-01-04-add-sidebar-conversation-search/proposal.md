# Change: 사이드바 대화 검색 기능 추가

## Why

현재 사이드바에 검색창 UI가 있지만 기능이 구현되어 있지 않다. 사용자가 참여 중인 대화방의 모든 메시지에서 키워드를 검색하여 원하는 대화를 빠르게 찾을 수 있도록 검색 기능을 구현해야 한다.

## What Changes

- 사이드바 검색창에 대화방 메시지 검색 기능 추가
- 참여 중인 모든 대화방의 메시지 내용에서 검색
- 검색 결과: 일치하는 메시지가 있는 대화방 목록 표시
- 대화 요약(일치하는 메시지 미리보기)에 검색어 하이라이트 표시
- 서버 사이드 검색 API 구현 (pg_trgm + GIN 인덱스 활용)

## Impact

- Affected specs: `sidebar-search` (신규)
- Affected code:
  - `apps/chat/models.py` - RoomQuerySet에 메시지 검색 메서드 추가
  - `apps/chat/apis.py` - 대화방 검색 API 엔드포인트 추가
  - `templates/chat/room.html` - 사이드바 검색 UI 바인딩
  - `static/js/chat/index.js` - Alpine.js 검색 로직 추가
