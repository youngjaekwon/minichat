# Design: 대화방 기본 기능

## Context

minichat은 실시간 채팅 애플리케이션이지만, 이 단계에서는 WebSocket 없이 전통적인 HTTP 요청/응답 방식으로 대화방 기본 구조를 구축한다. 1:1 대화와 그룹 대화를 모두 지원하되, 읽음/안읽음 상태 추적은 추후 단계에서 구현한다.

## Goals / Non-Goals

**Goals**:
- Room, Message 모델 생성 및 관계 정의
- 1:1 대화 및 그룹 대화 지원 (is_direct 플래그로 구분)
- 대화 목록에서 마지막 메시지 미리보기 표시
- Fat Model 패턴에 따른 비즈니스 로직 배치

**Non-Goals**:
- WebSocket 실시간 메시지 전송 (다음 단계에서 구현)
- 읽음/안읽음 상태 추적 (다음 단계에서 구현)
- 메시지 검색 기능
- 파일/이미지 첨부 기능

## Decisions

### 모델 구조

**Room 모델**:
- `name`: 대화방 이름 (그룹 대화용, 최대 100자, 빈 값 허용)
- `participants`: User M:N 관계
- `is_direct`: 1:1 대화 여부 (Boolean, 기본값 True)
- `created_by`: 대화방 생성자 (User ForeignKey)
- `created_at`, `updated_at`: 타임스탬프

1:1 대화는 `is_direct=True`, name 빈 값. 그룹 대화는 `is_direct=False`, name 필수.

**Message 모델**:
- `room`: Room ForeignKey
- `sender`: User ForeignKey
- `content`: 메시지 내용 (TextField)
- `created_at`: 전송 시간

**Alternatives considered**:
- RoomMembership through 테이블: 읽음 상태, 알림 설정 등을 위해 추후 확장 가능. 현 단계에서는 단순 ManyToManyField로 시작.

### 대화 목록 표시 규칙

- 1:1 대화: 상대방 이름으로 표시
- 그룹 대화: 대화방 이름으로 표시
- 마지막 메시지 미리보기 (최대 50자)
- 시간 표시: 오늘이면 시간만, 이전이면 날짜

### URL 구조

```
/chat/                      # 대화 목록
/chat/new/                  # 새 대화 시작 (상대방 선택)
/chat/<room_id>/            # 대화 상세 (메시지 목록)
/chat/<room_id>/send/       # 메시지 전송 (POST only)
```

### 뷰 패턴

Fat Model 패턴에 따라:
- `RoomManager`: 대화방 조회(`get_by_user`, `get_or_create_direct`) 및 생성(`create_room`) 로직
- `MessageManager`: 메시지 조회(`get_by_room`) 및 생성(`create_message`) 로직
- View: HTTP 처리만 담당, Manager 메서드 호출

### 1:1 대화 중복 방지

동일한 두 사용자 간 1:1 대화방이 여러 개 생성되지 않도록 `get_or_create_direct` 메서드를 사용한다.

### 인증 요구사항

- 모든 채팅 관련 페이지는 로그인 필수 (`@login_required`)
- 대화방 접근 권한 검증: 참여자만 상세 페이지 및 메시지 전송 가능

## Risks / Trade-offs

- **새로고침 방식의 UX**: 메시지 전송 후 페이지 새로고침은 사용자 경험이 좋지 않음. 추후 WebSocket으로 개선 예정.
- **성능**: 대량 메시지 시 페이지 로딩이 느려질 수 있음. 페이지네이션으로 완화.

## Open Questions

없음.
