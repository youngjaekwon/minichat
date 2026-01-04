/**
 * 채팅 애플리케이션 메인 컴포넌트
 */

import { formatTime, formatRoomTime } from './modules/dateUtils.js';
import { createWebSocketManager } from './modules/websocket.js';
import { createMessageManager } from './modules/messages.js';
import { createSearchManager } from './modules/search.js';
import { createScrollManager } from './modules/scroll.js';

/**
 * 채팅 앱 컴포넌트 생성
 * @param {number|null} roomId - 채팅방 ID
 * @param {number} userId - 사용자 ID
 * @param {string} userName - 사용자 이름
 * @returns {Object} Alpine.js 컴포넌트 객체
 */
export default function chatApp(roomId, userId, userName) {
    return {
        // 설정
        roomId: roomId,
        userId: userId,
        userName: userName,
        maxMessageLength: 10000,

        // 채팅방 목록 상태
        rooms: [],
        isLoadingRooms: true,

        // 사이드바 상태 (모바일용)
        sidebarOpen: false,

        // 연결 상태
        connectionState: 'disconnected',
        reconnectAttempts: 0,

        // 메시지
        messageInput: '',
        messages: [],
        lastMessageId: null,
        lastDate: null,

        // 초기 로딩 상태
        isInitialLoading: true,
        isAtLatest: true,

        // 무한 스크롤 상태 (스크롤 업)
        oldMessages: [],
        isLoadingMore: false,
        hasMore: false,
        oldestMessageId: null,

        // 무한 스크롤 상태 (스크롤 다운)
        hasMoreAfter: false,
        newestMessageId: null,
        isLoadingMoreAfter: false,

        // 에러 표시
        errorMessage: null,
        errorTimeout: null,

        // 새 메시지 토스트 상태
        isNearBottom: true,
        showNewMessageToast: false,
        newMessageCount: 0,

        // 검색 상태
        isSearchOpen: false,
        searchQuery: '',
        searchResults: [],
        searchCurrentIndex: 0,
        isSearching: false,
        searchPerformed: false,

        // 매니저 인스턴스
        wsManager: null,
        messageManager: null,
        searchManager: null,
        scrollManager: null,

        /**
         * 컴포넌트 초기화
         */
        async init() {
            // 채팅방 목록 로드
            await this.loadRooms();

            // 모바일에서 대화가 선택되지 않았을 때 사이드바 자동 표시
            if (!this.roomId) {
                if (window.innerWidth < 768) {
                    this.sidebarOpen = true;
                }
                return;
            }

            // 매니저 초기화
            this.wsManager = createWebSocketManager(this);
            this.messageManager = createMessageManager(this);
            this.searchManager = createSearchManager(this);
            this.scrollManager = createScrollManager(this);

            // 스크롤 이벤트 리스너 등록
            this.$nextTick(() => {
                const container = this.$refs.messagesContainer;
                if (container) {
                    container.addEventListener('scroll', () =>
                        this.scrollManager.handleScroll()
                    );
                }
            });

            // 페이지 언로드 시 연결 종료
            window.addEventListener('beforeunload', () => this.disconnect());

            // 초기 메시지 로드 후 WebSocket 연결
            await this.messageManager.loadInitialMessages();
            this.wsManager.connect();
            this.scrollManager.setupInfiniteScroll();
        },

        // ==================== 사이드바 ====================

        /**
         * 사이드바 토글
         */
        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
        },

        /**
         * 사이드바 닫기
         */
        closeSidebar() {
            this.sidebarOpen = false;
        },

        /**
         * 채팅방 목록 로드
         */
        async loadRooms() {
            this.isLoadingRooms = true;

            try {
                const response = await fetch('/chat/api/rooms/');

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                this.rooms = data.rooms || [];
            } catch (error) {
                console.error('Failed to load rooms:', error);
                this.showError('대화 목록을 불러오는데 실패했습니다.');
            } finally {
                this.isLoadingRooms = false;
            }
        },

        // ==================== 연결 ====================

        /**
         * 연결 종료
         */
        disconnect() {
            this.scrollManager?.disconnect();
            this.wsManager?.disconnect();
        },

        // ==================== 메시지 ====================

        /**
         * 메시지 전송
         */
        sendMessage() {
            this.messageManager?.sendMessage();
        },

        // ==================== 검색 ====================

        /**
         * 검색 토글
         */
        toggleSearch() {
            this.searchManager?.toggleSearch();
        },

        /**
         * 검색 닫기
         */
        closeSearch() {
            this.searchManager?.closeSearch();
        },

        /**
         * 검색 결과 초기화
         */
        clearSearchResults() {
            this.searchManager?.clearSearchResults();
        },

        /**
         * 검색 수행
         */
        performSearch() {
            this.searchManager?.performSearch();
        },

        /**
         * 검색 결과 네비게이션
         * @param {number} direction - 1: 다음, -1: 이전
         */
        navigateSearch(direction) {
            this.searchManager?.navigateSearch(direction);
        },

        // ==================== 스크롤 ====================

        /**
         * 맨 아래로 스크롤
         */
        scrollToBottom() {
            this.scrollManager?.scrollToBottom();
        },

        /**
         * 토스트 클릭 시 맨 아래로 스크롤
         */
        scrollToBottomAndHideToast() {
            this.scrollManager?.scrollToBottomAndHideToast();
        },

        // ==================== 유틸리티 ====================

        /**
         * 시간 포맷팅
         * @param {string} isoString - ISO 8601 형식의 날짜 문자열
         * @returns {string} 포맷팅된 시간 문자열
         */
        formatTime(isoString) {
            return formatTime(isoString);
        },

        /**
         * 채팅방 목록용 시간 포맷팅
         * @param {string} isoString - ISO 8601 형식의 날짜 문자열
         * @param {boolean} isToday - 오늘 날짜 여부
         * @returns {string} 포맷팅된 시간 또는 날짜 문자열
         */
        formatRoomTime(isoString, isToday) {
            return formatRoomTime(isoString, isToday);
        },

        /**
         * 에러 메시지 표시
         * @param {string} message - 에러 메시지
         */
        showError(message) {
            this.errorMessage = message;

            if (this.errorTimeout) {
                clearTimeout(this.errorTimeout);
            }
            this.errorTimeout = setTimeout(() => {
                this.errorMessage = null;
            }, 3000);
        },
    };
}
