## Context

사용자 간 메시지 읽음 여부 확인이 필요하며, 사이드바에 실시간으로 새 메시지 상태를 반영해야 한다. 기존 WebSocket 인프라(Django Channels, Redis)를 활용하여 구현한다.

**제약사항**:
- 대규모 그룹 채팅에서도 성능 유지 필요
- 기존 채팅 기능에 영향 최소화
- 모바일 환경에서도 원활한 동작

## Goals / Non-Goals

**Goals**:
- 메시지별 읽음 상태 추적
- 채팅창에서 안읽은 인원 수 실시간 표시
- 사이드바에서 채팅방별 안읽은 메시지 수 및 미리보기 실시간 갱신
- 새 메시지 기준 채팅방 정렬 (검색 모드 제외)

**Non-Goals**:
- 읽음 상세 보기 (누가 읽었는지 목록) - 추후 확장 가능
- 읽음 시간 표시 (언제 읽었는지)
- 푸시 알림

## Decisions

### 1. MessageRead 모델 설계

**Decision**: 별도 MessageRead 중간 테이블 사용

```python
class MessageRead(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'read_at']),
        ]
```

**Alternatives**:
- Message에 read_by ManyToManyField 추가: 단순하지만 읽음 시간 추적 불가
- JSON 필드로 읽은 사용자 저장: 조회 성능 문제

**Rationale**: 별도 테이블이 인덱싱과 쿼리 최적화에 유리하고, 향후 확장(읽음 시간 등)에 용이함.

### 2. 읽음 처리 시점

**Decision**: 대화방 WebSocket 연결 시 자동으로 안읽은 메시지 일괄 읽음 처리

**Flow**:
1. 사용자가 대화방에 입장 (WebSocket 연결)
2. 해당 방의 자신이 보낸 메시지를 제외한 안읽은 메시지 조회
3. 일괄 읽음 처리 (bulk_create)
4. **Celery task로 발신자들에게 읽음 상태 변경 비동기 브로드캐스트**

**Rationale**: 스크롤 기반 읽음 처리는 구현 복잡도가 높고, 대부분의 사용 사례에서 방 입장 = 메시지 확인으로 충분함. 브로드캐스트를 Celery로 비동기 처리하여 연결 응답 지연을 방지함.

### 3. 안읽은 인원 수 계산

**Decision**: 메시지 조회 시 annotate로 안읽은 수 계산

```python
Message.objects.annotate(
    unread_count=Count('room__participants') - Count('reads') - 1  # 발신자 제외
)
```

**Alternatives**:
- Message 모델에 unread_count 필드 추가 및 동기화: 데이터 정합성 문제 위험
- 캐싱: Redis에 읽음 수 캐싱: 복잡도 증가

**Rationale**: 실시간 정확성이 중요하고, 적절한 인덱싱으로 쿼리 성능 확보 가능.

### 4. 사이드바 실시간 갱신 방식

**Decision**: 기존 ChatConsumer에 사이드바 업데이트 브로드캐스트 추가 + 사용자별 Channel Group + Celery 비동기 처리

**구조**:
```
chat_room_{room_id}        # 기존: 대화방 내 메시지 브로드캐스트 (동기)
user_chat_rooms_{user_id}  # 신규: 사용자별 사이드바 업데이트 (Celery 비동기)
```

**Flow** (새 메시지 수신 시):
1. 메시지가 DB에 저장됨
2. `chat_room_{room_id}` 그룹에 메시지 브로드캐스트 (기존, 동기)
3. Celery task 호출: 해당 방의 모든 참여자 `user_chat_rooms_{user_id}` 그룹에 사이드바 업데이트 비동기 브로드캐스트

**Flow** (메시지 읽음 처리 시):
1. 대화방 입장 시 안읽은 메시지 일괄 읽음 처리 (DB)
2. Celery task 호출: 각 메시지 발신자에게 읽음 상태 변경 비동기 브로드캐스트

**Alternatives**:
- 동기 브로드캐스트: 참여자가 많을 경우 응답 지연
- 별도 SidebarConsumer: WebSocket 연결 2개 필요, 리소스 낭비
- Polling: 실시간성 저하, 서버 부하

**Rationale**:
- Celery 비동기 처리로 메시지 전송/연결 응답 지연 방지
- 참여자가 많은 그룹에서 특히 효과적
- 기존 Celery + Redis 인프라 활용

### 5. 검색 중 정렬 유지

**Decision**: 프론트엔드에서 `isSearching` 상태에 따라 정렬 로직 조건부 적용

- `isSearching === true`: 사이드바 순서 유지, 배지만 업데이트
- `isSearching === false`: 새 메시지 있는 채팅방 최상단으로 이동

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| MessageRead 테이블 급격한 증가 | 스토리지, 쿼리 성능 | 주기적 정리 또는 파티셔닝 고려 |
| 대규모 그룹에서 읽음 브로드캐스트 부하 | WebSocket 성능 | 그룹 크기에 따른 throttling 검토 |
| 오프라인 상태에서 읽음 처리 누락 | UX | 재연결 시 동기화 |

## Migration Plan

1. MessageRead 모델 마이그레이션 생성 및 적용
2. 기존 메시지에 대한 읽음 상태 초기화는 하지 않음 (새 메시지부터 적용)
3. 점진적 배포: 읽음 기능 비활성화 상태로 배포 후 feature flag로 활성화

## Open Questions

- 대규모 그룹(100명+)에서 성능 테스트 필요
- 장기 보관된 메시지의 MessageRead 정리 정책
