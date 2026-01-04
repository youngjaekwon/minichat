# Change: 채팅방 메시지 검색 기능 추가

## Why

현재 채팅방에서 과거 메시지를 찾으려면 직접 스크롤하여 찾아야 한다. 대화가 길어질수록 특정 메시지를 찾기 어려워지므로, 키워드 기반 메시지 검색 기능이 필요하다.

## What Changes

- PostgreSQL pg_trgm 확장과 GIN 인덱스를 활용한 메시지 검색 기능 추가
- `__icontains` 기반 부분 일치 검색 지원
- 검색 결과 네비게이션 (이전/다음 결과로 이동)
- 검색된 메시지 하이라이트 표시

## Impact

- Affected specs: 새로운 `message-search` capability 추가
- Affected code:
  - `apps/chat/models.py` - MessageQuerySet에 검색 메서드 추가
  - `apps/chat/apis.py` - 검색 API 엔드포인트 추가
  - `apps/chat/serializers.py` - 검색 파라미터/응답 직렬화
  - `templates/chat/room.html` - 검색 UI 컴포넌트 추가
  - Migration 파일 - GIN 인덱스 추가
