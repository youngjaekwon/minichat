## 1. Backend - 검색 API 구현

- [x] 1.1 RoomManager에 search_by_message 메서드 추가 (메시지 내용으로 대화방 검색)
- [x] 1.2 대화방 검색 API 엔드포인트 구현 (`GET /chat/api/rooms/search/`)
- [x] 1.3 검색 API 테스트 작성

## 2. Frontend - Alpine.js 검색 로직

- [x] 2.1 chatApp 컴포넌트에 sidebarSearchQuery 상태 추가
- [x] 2.2 searchRooms() 메서드 구현 (API 호출 + 디바운스)
- [x] 2.3 searchResults 상태 및 검색 모드 관리
- [x] 2.4 highlightText 헬퍼 함수 추가 (검색어 하이라이트 처리)

## 3. Frontend - 템플릿 UI 연동

- [x] 3.1 사이드바 검색창에 x-model 바인딩 및 이벤트 핸들러 연결
- [x] 3.2 검색 모드일 때 검색 결과 목록 렌더링
- [x] 3.3 메시지 미리보기에 하이라이트 적용
- [x] 3.4 검색 결과 없음 상태 표시

## 4. 검증

- [x] 4.1 메시지 내용 검색 동작 확인
- [x] 4.2 검색어 하이라이트 표시 확인
- [x] 4.3 검색어 삭제 시 원래 목록 복원 확인
- [x] 4.4 검색 결과 없음 표시 확인
