# WebSocket Close Codes
CLOSE_CODE_UNAUTHORIZED = 4001
CLOSE_CODE_FORBIDDEN = 4003
CLOSE_CODE_NOT_FOUND = 4004

# Error Codes
ERROR_EMPTY_MESSAGE = "EMPTY_MESSAGE"
ERROR_INVALID_FORMAT = "INVALID_FORMAT"

# Message Limits
MAX_MESSAGE_LENGTH = 10000

# Sync/Pagination Limits
MAX_SYNC_MESSAGES = 50  # 초기 로드 및 재연결 시 동기화 메시지 수
MESSAGES_PER_PAGE = 50  # 무한 스크롤 시 페이지당 로드 개수
ROOMS_PER_PAGE = 20  # 대화방 목록 페이지당 로드 개수

# Sliding Window
SLIDING_WINDOW_SIZE = 150  # 슬라이딩 윈도우 최대 메시지 수
SLIDING_WINDOW_BUFFER = 50  # 언로드 시 유지할 버퍼 크기
