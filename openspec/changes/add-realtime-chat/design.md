# Design: Realtime Chat

## Context

현재 채팅 시스템은 Form POST로 메시지를 전송하고 페이지 새로고침으로 메시지를 확인한다. Django Channels와 Redis Channel Layer가 이미 설정되어 있으므로 이를 활용하여 WebSocket 기반 실시간 통신을 구현한다.

**기존 인프라**:
- Django Channels 4.x, Daphne 4.x (pyproject.toml)
- Redis Channel Layer 설정 (config/settings/base.py)
- ASGI 설정 (config/asgi.py) - websocket_urlpatterns 빈 배열

## Goals / Non-Goals

**Goals**:
- WebSocket을 통한 실시간 메시지 송수신
- 대화방 참여자 전원에게 메시지 브로드캐스트
- 인증된 참여자만 WebSocket 연결 허용
- Alpine.js로 프론트엔드 WebSocket 클라이언트 구현
- 연결 끊김 시 자동 재연결 및 메시지 동기화
- Rate Limiting으로 악용 방지

**Non-Goals**:
- 읽음 확인 (read receipts)
- 타이핑 인디케이터
- 파일/이미지 전송
- 푸시 알림

## Decisions

### 1. AsyncWebsocketConsumer 사용

**결정**: `AsyncWebsocketConsumer` 기반으로 ChatConsumer 구현

**이유**:
- Django ORM은 sync_to_async로 래핑하여 호출
- async/await로 비동기 I/O 처리 가능
- Channel Layer 호출이 native async

### 2. WebSocket 인증

**결정**: `AuthMiddlewareStack` 사용

**이유**:
- Django 세션 기반 인증을 WebSocket에도 적용
- `self.scope["user"]`로 인증된 사용자 접근 가능
- 추가 토큰 인증 불필요 (세션 쿠키 자동 전달)

**ASGI 설정 수정 필요**:
```python
from channels.auth import AuthMiddlewareStack

"websocket": AllowedHostsOriginValidator(
    AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
),
```

### 3. Channel Layer 그룹 명명

**결정**: `chat_room_{room_id}` 형식

**이유**:
- Room PK 기반으로 고유한 그룹 생성
- 해당 대화방 참여자에게만 메시지 브로드캐스트

### 4. 메시지 포맷 (WebSocket)

**결정**: JSON 형식, 클라이언트 ID 기반 ACK 지원

```json
// 클라이언트 → 서버 (전송)
{
    "type": "chat_message",
    "content": "메시지 내용",
    "client_id": "uuid-v4"  // 클라이언트 생성 임시 ID (ACK용)
}

// 서버 → 클라이언트 (메시지 수신)
{
    "type": "chat_message",
    "message": {
        "id": 123,
        "content": "메시지 내용",
        "sender_id": 1,
        "sender_name": "홍길동",
        "created_at": "2026-01-04T12:30:00+09:00"
    }
}

// 서버 → 클라이언트 (전송 확인)
{
    "type": "message_ack",
    "client_id": "uuid-v4",
    "message_id": 123,
    "status": "success"
}

// 서버 → 클라이언트 (에러)
{
    "type": "error",
    "code": "EMPTY_MESSAGE",
    "message": "메시지 내용이 비어있습니다."
}
```

**에러 코드 목록**:
| 코드 | 설명 |
|------|------|
| EMPTY_MESSAGE | 빈 메시지 전송 시도 |
| RATE_LIMITED | 전송 제한 초과 |
| INVALID_FORMAT | JSON 파싱 실패 |

**이유**:
- 프론트엔드에서 메시지 렌더링에 필요한 정보 포함
- 시간 정보 ISO 8601 형식으로 표준화
- client_id로 전송 성공/실패 확인 가능

### 5. WebSocket Close Codes

| 코드 | 의미 | 사용 시점 |
|------|------|-----------|
| 4001 | Unauthorized | 비인증 사용자 연결 시도 |
| 4003 | Forbidden | 비참여자 연결 시도 |
| 4004 | Room Not Found | 존재하지 않는 대화방 |
| 4029 | Rate Limited | 연결 수 제한 초과 |

### 6. 프론트엔드 구현

**결정**: Alpine.js x-data 컴포넌트로 WebSocket 클라이언트 구현

**이유**:
- 프로젝트 기술 스택에 Alpine.js 포함
- 경량 반응형 UI에 적합
- 템플릿과 자연스럽게 통합

### 7. 재연결 정책 (Exponential Backoff)

**결정**: 지수 백오프 기반 자동 재연결

**파라미터**:
| 항목 | 값 |
|------|-----|
| 초기 지연 | 1초 |
| 최대 지연 | 30초 |
| 백오프 계수 | 2 |
| 최대 재시도 횟수 | 10회 |
| Jitter | 무작위 0-1초 추가 |

**재연결 시 메시지 동기화**:
- 클라이언트가 마지막으로 수신한 메시지 ID를 로컬에 저장
- 재연결 시 쿼리 파라미터로 `last_message_id` 전송
- Consumer connect()에서 누락된 메시지 조회 후 순차 전송

### 8. Rate Limiting

**결정**: 사용자별 메시지 전송 제한

**제한**:
| 항목 | 값 |
|------|-----|
| 분당 최대 메시지 | 60개 |
| 연속 전송 제한 | 1초당 5개 |

**구현 방식**:
- Redis를 활용한 sliding window counter
- 제한 초과 시 에러 응답 + 재시도 대기 시간 안내

### 9. Heartbeat (연결 상태 확인)

**결정**: 서버 주도 Ping-Pong 방식

**파라미터**:
| 항목 | 값 |
|------|-----|
| Ping 주기 | 30초 |
| Pong 타임아웃 | 10초 |

**동작**:
- 서버가 30초마다 ping 전송
- 클라이언트가 10초 내 pong 미응답 시 연결 종료
- 클라이언트 측에서도 연결 끊김 감지 후 재연결 시도

### 10. 수평 확장 전략

**결정**: Redis Channel Layer를 통한 크로스 서버 메시지 라우팅

**Redis Channel Layer 권장 설정**:
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,       # 그룹당 최대 메시지 수
            "expiry": 10,           # 메시지 만료 시간 (초)
            "group_expiry": 86400,  # 그룹 만료 시간 (24시간)
        },
    },
}
```

**고려사항**:
- 모든 Daphne 인스턴스가 동일한 Redis 인스턴스 사용
- 프로덕션 환경에서 Redis Sentinel 또는 Cluster 구성 고려 (고가용성)
- 연결 수 모니터링 및 인스턴스별 부하 분산

## Risks / Trade-offs

| 리스크 | 완화 방안 |
|--------|----------|
| WebSocket 연결 끊김 | Exponential backoff 재연결 + 메시지 동기화 |
| 메시지 유실 | DB 저장 후 브로드캐스트 + 재연결 시 동기화 |
| 비인증 접근 | AuthMiddlewareStack + connect()에서 검증, 실패 시 close(4001) |
| 악의적 대량 전송 | Rate Limiting (분당 60개, 초당 5개) |
| 좀비 연결 | Heartbeat ping-pong으로 감지 및 정리 |
| 수평 확장 시 메시지 전달 | Redis Channel Layer 그룹 브로드캐스트 |
