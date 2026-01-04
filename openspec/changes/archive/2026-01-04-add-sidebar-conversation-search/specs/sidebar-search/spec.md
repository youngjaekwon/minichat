## ADDED Requirements

### Requirement: Conversation Search API

시스템은 사용자가 참여 중인 대화방의 메시지를 검색하는 API를 제공해야 한다(SHALL).

- URL: `GET /chat/api/rooms/search/`
- Query Parameters:
  - `q`: 검색어 (필수, 최소 2자)
- Response: 일치하는 메시지가 있는 대화방 목록
  - 대화방 ID, 표시 이름, 일치하는 메시지 미리보기
- 검색 범위: 사용자가 참여 중인 모든 대화방의 모든 메시지
- 대소문자 구분 없이 검색 (case-insensitive)
- pg_trgm + GIN 인덱스 활용

#### Scenario: 메시지 검색 성공

- **WHEN** 사용자가 유효한 검색어로 검색하면
- **THEN** 일치하는 메시지가 있는 대화방 목록이 반환되어야 한다
- **AND** 각 대화방에 일치하는 메시지 미리보기가 포함되어야 한다

#### Scenario: 검색어 누락

- **WHEN** 검색어 없이 API를 호출하면
- **THEN** 400 Bad Request 응답이 반환되어야 한다

#### Scenario: 검색어 길이 미달

- **WHEN** 1자 검색어로 API를 호출하면
- **THEN** 400 Bad Request 응답이 반환되어야 한다

#### Scenario: 검색 결과 없음

- **WHEN** 일치하는 메시지가 없으면
- **THEN** 빈 목록이 반환되어야 한다


### Requirement: Sidebar Search UI

시스템은 사이드바에서 대화를 검색하는 UI를 제공해야 한다(SHALL).

- 사이드바 검색창에 키워드 입력 시 검색 API 호출
- 검색 결과: 일치하는 메시지가 있는 대화방 목록으로 교체
- 검색어 삭제 시 원래 대화방 목록으로 복원
- 디바운스 적용하여 불필요한 API 호출 방지

#### Scenario: 검색 실행

- **WHEN** 사용자가 사이드바 검색창에 2자 이상 입력하면
- **THEN** 검색 API가 호출되어야 한다
- **AND** 검색 결과로 대화방 목록이 교체되어야 한다

#### Scenario: 검색어 삭제

- **WHEN** 사용자가 검색어를 모두 삭제하면
- **THEN** 원래 대화방 목록이 다시 표시되어야 한다

#### Scenario: 검색 결과 없음 표시

- **WHEN** 검색 결과가 없으면
- **THEN** 빈 상태 메시지가 표시되어야 한다


### Requirement: Search Keyword Highlight

시스템은 검색 결과의 메시지 미리보기에서 검색어를 하이라이트해야 한다(SHALL).

- 검색어와 일치하는 부분에 시각적 강조 스타일 적용
- 대소문자 무관하게 일치하는 모든 부분 하이라이트
- 검색어가 없으면 하이라이트 없이 일반 표시

#### Scenario: 검색어 하이라이트 표시

- **WHEN** 검색 결과의 메시지 미리보기가 표시되면
- **THEN** 검색어와 일치하는 부분이 하이라이트되어야 한다

#### Scenario: 검색어 하이라이트 해제

- **WHEN** 검색어가 비워지면
- **THEN** 모든 하이라이트가 제거되고 원래 대화방 목록이 표시되어야 한다
