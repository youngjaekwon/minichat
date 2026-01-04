## 1. 데이터베이스 설정

- [x] 1.1 pg_trgm 확장 활성화 마이그레이션 생성
- [x] 1.2 Message.content에 GIN 인덱스 추가 마이그레이션 생성
- [x] 1.3 마이그레이션 적용 및 검증

## 2. 백엔드 구현

- [x] 2.1 MessageQuerySet에 `search(query)` 메서드 추가
- [x] 2.2 검색 파라미터 Serializer 작성 (MessageSearchParamsSerializer)
- [x] 2.3 검색 API 엔드포인트 구현 (MessageSearchAPIView)
- [x] 2.4 URL 라우팅 추가 (`/chat/api/{room_id}/messages/search/`)

## 3. 백엔드 테스트

- [x] 3.1 검색 QuerySet 단위 테스트 작성
- [x] 3.2 검색 API 통합 테스트 작성
- [x] 3.3 권한 검증 테스트 작성

## 4. 프론트엔드 구현

- [x] 4.1 검색 상태 관리 변수 추가 (Alpine.js)
- [x] 4.2 헤더에 검색 버튼 추가
- [x] 4.3 검색 바 컴포넌트 구현 (입력 필드, 카운터, 네비게이션 버튼)
- [x] 4.4 검색 API 호출 함수 구현
- [x] 4.5 검색 결과 네비게이션 로직 구현 (이전/다음)
- [x] 4.6 메시지 하이라이트 스타일 및 스크롤 로직 구현
- [x] 4.7 키보드 단축키 구현 (Enter, Shift+Enter, Escape)
