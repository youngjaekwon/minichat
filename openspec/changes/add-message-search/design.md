## Context

채팅방 내 메시지 검색 기능을 추가한다. 대화가 길어질수록 특정 메시지를 찾기 어려우므로, 키워드 기반 검색과 결과 네비게이션이 필요하다.

**기존 인프라**:
- PostgreSQL 16 (Full-text Search, GIN Index 지원)
- Message 모델에 content TextField 존재
- MessageListAPIView에 cursor 기반 pagination 구현됨

## Goals / Non-Goals

**Goals**:
- 현재 대화방 내 메시지를 키워드로 검색
- 검색 결과 간 이전/다음 네비게이션
- 검색된 메시지 위치로 스크롤 및 하이라이트

**Non-Goals**:
- 전체 대화방을 대상으로 한 글로벌 검색
- 복잡한 쿼리 문법 (AND/OR/NOT 등)
- 검색어 자동완성

## Decisions

### 1. 검색 방식: pg_trgm + GIN Index + `__icontains`

- **결정**: PostgreSQL pg_trgm 확장과 GIN 인덱스를 사용한 `__icontains` 검색
- **이유**:
  - 한글 부분 일치 검색 지원
  - 대용량 데이터에서도 빠른 검색 성능
  - Django ORM과 자연스럽게 통합
- **대안 검토**:
  - Full-text Search (tsvector): 영어에 최적화되어 있고 한글 형태소 분석기가 필요
  - LIKE 쿼리: 인덱스 미사용으로 성능 저하

### 2. 검색 API 구조

- **결정**: 새로운 검색 엔드포인트 추가
  - `GET /chat/api/{room_id}/messages/search/?q={query}`
  - 검색 결과는 메시지 ID 목록만 반환 (경량화)
  - 실제 메시지 조회는 기존 `messages/?direction=around&cursor={id}` 활용
- **이유**:
  - 기존 pagination 로직 재사용
  - 프론트엔드에서 검색 결과 캐싱 용이

### 3. 검색 UI 배치

- **결정**: 대화방 헤더에 검색 버튼 → 클릭 시 검색 바 표시
- **이유**:
  - 헤더 공간 효율적 활용
  - 검색 중에도 메시지 영역 최대화

### 4. 네비게이션 인디케이터

- **결정**: 검색 바 내에 인디케이터 배치 (예: "3/15", ▲, ▼ 버튼)
- **이유**:
  - 검색 컨텍스트와 네비게이션을 한 곳에서 제공
  - 플로팅 UI 대비 구현 단순화

## Risks / Trade-offs

| 리스크 | 완화 방안 |
|--------|-----------|
| pg_trgm 인덱스 생성 시 마이그레이션 시간 | CREATE INDEX CONCURRENTLY 사용 |
| 검색어가 매우 짧을 때 (1-2자) 성능 저하 | 최소 검색어 길이 2자로 제한 |
| 동시 검색 + 실시간 메시지 수신 시 UX 복잡성 | 새 메시지 수신 시 검색 결과 유지, 필요시 재검색 안내 |

## Migration Plan

1. pg_trgm 확장 활성화 마이그레이션
2. Message.content에 GIN 인덱스 추가 마이그레이션
3. 검색 API 배포
4. 프론트엔드 검색 UI 배포

롤백: 마이그레이션 역방향 적용으로 인덱스 제거 (기능 비활성화)

## Open Questions

없음
