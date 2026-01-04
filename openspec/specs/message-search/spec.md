# message-search Specification

## Purpose
TBD - created by archiving change add-message-search. Update Purpose after archive.
## Requirements
### Requirement: Message Search Index

시스템은 메시지 검색을 위한 PostgreSQL pg_trgm 확장과 GIN 인덱스를 제공해야 한다(SHALL).

- pg_trgm 확장 활성화
- Message.content 필드에 GIN 인덱스 적용
- trigram 기반 부분 일치 검색 지원

#### Scenario: Trigram 인덱스 적용

- **WHEN** Message 테이블에 GIN 인덱스가 적용되면
- **THEN** `__icontains` 쿼리가 인덱스를 활용해야 한다

### Requirement: Message Search QuerySet

시스템은 메시지 검색을 위한 QuerySet 메서드를 제공해야 한다(SHALL).

- `search(query)` 메서드: 키워드로 메시지 검색
- 대소문자 구분 없이 검색 (case-insensitive)
- 생성 시간 오름차순 정렬

#### Scenario: 키워드 검색

- **WHEN** `Message.objects.for_room(room).search("회의")`를 호출하면
- **THEN** "회의"를 포함하는 메시지가 반환되어야 한다
- **AND** 생성 시간 오름차순으로 정렬되어야 한다

#### Scenario: 빈 검색어

- **WHEN** 빈 문자열로 검색하면
- **THEN** 빈 QuerySet이 반환되어야 한다

#### Scenario: 최소 검색어 길이

- **WHEN** 1자 검색어로 검색하면
- **THEN** 빈 QuerySet이 반환되어야 한다

### Requirement: Message Search API

시스템은 대화방 내 메시지 검색 API를 제공해야 한다(SHALL).

- URL: `GET /chat/api/{room_id}/messages/search/`
- Query Parameters:
  - `q`: 검색어 (필수, 최소 2자)
- Response: 검색된 메시지 ID 목록 (시간순)
- 권한: 대화방 참여자만 접근 가능

#### Scenario: 메시지 검색 성공

- **WHEN** 참여자가 유효한 검색어로 검색하면
- **THEN** 일치하는 메시지 ID 목록이 반환되어야 한다
- **AND** 생성 시간 오름차순으로 정렬되어야 한다

#### Scenario: 검색어 누락

- **WHEN** 검색어 없이 API를 호출하면
- **THEN** 400 Bad Request 응답이 반환되어야 한다

#### Scenario: 검색어 길이 미달

- **WHEN** 1자 검색어로 API를 호출하면
- **THEN** 400 Bad Request 응답이 반환되어야 한다

#### Scenario: 비참여자 검색 시도

- **WHEN** 대화방에 참여하지 않은 사용자가 검색하면
- **THEN** 403 Forbidden 응답이 반환되어야 한다

#### Scenario: 검색 결과 없음

- **WHEN** 일치하는 메시지가 없으면
- **THEN** 빈 목록이 반환되어야 한다

### Requirement: Search UI Component

시스템은 대화방 헤더에 메시지 검색 UI를 제공해야 한다(SHALL).

- 헤더에 검색 버튼 표시
- 버튼 클릭 시 검색 바 표시/숨김 토글
- 검색 바에 입력 필드, 결과 카운터, 이전/다음 버튼 포함

#### Scenario: 검색 바 토글

- **WHEN** 사용자가 검색 버튼을 클릭하면
- **THEN** 검색 바가 표시되어야 한다
- **AND** 다시 클릭하면 검색 바가 숨겨져야 한다

#### Scenario: 검색 실행

- **WHEN** 사용자가 검색어를 입력하고 Enter를 누르면
- **THEN** 검색이 실행되어야 한다
- **AND** 첫 번째 결과로 스크롤되어야 한다

#### Scenario: 검색 결과 카운터

- **WHEN** 검색 결과가 있으면
- **THEN** "현재 위치/전체 개수" 형식으로 표시되어야 한다 (예: "1/15")

#### Scenario: 검색 결과 없음 표시

- **WHEN** 검색 결과가 없으면
- **THEN** "0/0" 또는 "결과 없음"이 표시되어야 한다

### Requirement: Search Navigation

시스템은 검색 결과 간 네비게이션 기능을 제공해야 한다(SHALL).

- 이전 결과로 이동 (▲ 버튼)
- 다음 결과로 이동 (▼ 버튼)
- 순환 네비게이션 지원 (마지막 → 첫 번째)

#### Scenario: 다음 결과로 이동

- **WHEN** 사용자가 다음(▼) 버튼을 클릭하면
- **THEN** 다음 검색 결과 메시지로 스크롤되어야 한다
- **AND** 해당 메시지가 하이라이트되어야 한다

#### Scenario: 이전 결과로 이동

- **WHEN** 사용자가 이전(▲) 버튼을 클릭하면
- **THEN** 이전 검색 결과 메시지로 스크롤되어야 한다
- **AND** 해당 메시지가 하이라이트되어야 한다

#### Scenario: 순환 네비게이션

- **WHEN** 마지막 결과에서 다음(▼) 버튼을 클릭하면
- **THEN** 첫 번째 결과로 이동해야 한다

#### Scenario: 키보드 네비게이션

- **WHEN** 검색 바에 포커스가 있을 때 Enter를 누르면
- **THEN** 다음 결과로 이동해야 한다
- **WHEN** Shift+Enter를 누르면
- **THEN** 이전 결과로 이동해야 한다

### Requirement: Search Result Highlight

시스템은 현재 검색 결과 메시지를 시각적으로 강조해야 한다(SHALL).

- 현재 위치의 메시지에 하이라이트 스타일 적용
- 스크롤 시 해당 메시지가 화면 중앙에 위치

#### Scenario: 메시지 하이라이트

- **WHEN** 검색 결과로 이동하면
- **THEN** 해당 메시지에 하이라이트 배경색이 적용되어야 한다

#### Scenario: 검색 종료 시 하이라이트 제거

- **WHEN** 검색 바를 닫거나 검색어를 지우면
- **THEN** 모든 하이라이트가 제거되어야 한다

