/**
 * 채팅 애플리케이션 메인 컴포넌트
 */

import { formatTime } from './modules/dateUtils.js';
import { createWebSocketManager } from './modules/websocket.js';
import { createMessageManager } from './modules/messages.js';
import { createSearchManager } from './modules/search.js';
import { createScrollManager } from './modules/scroll.js';

/**
 * 채팅 앱 컴포넌트 생성
 * @param {number|null} roomId - 채팅방 ID
 * @param {number} userId - 사용자 ID
 * @param {string} userName - 사용자 이름
 * @param {number} participantCount - 참여자 수
 * @returns {Object} Alpine.js 컴포넌트 객체
 */
export default function chatApp(roomId, userId, userName, participantCount) {
    return {
        // 설정
        roomId: roomId,
        userId: userId,
        userName: userName,
        participantCount: participantCount,
        maxMessageLength: 10000,

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

        // 사이드바 채팅방 정보 (실시간 업데이트용)
        sidebarRooms: {},

        // 매니저 인스턴스
        wsManager: null,
        messageManager: null,
        searchManager: null,
        scrollManager: null,

        /**
         * 컴포넌트 초기화
         */
        async init() {
            // 모바일에서 대화가 선택되지 않았을 때 사이드바 자동 표시
            if (!this.roomId) {
                if (window.innerWidth < 768) {
                    this.sidebarOpen = true;
                }
                // 사이드바 업데이트를 위한 WebSocket 연결 (room 없이)
                this.wsManager = createWebSocketManager(this);
                this.wsManager.connectSidebarOnly();

                // 페이지 언로드 시 연결 종료
                window.addEventListener('beforeunload', () => this.disconnect());
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

        // ==================== 사이드바 업데이트 ====================

        /**
         * 사이드바 업데이트 처리
         * @param {Object} room - 채팅방 정보 (room_id, last_message, last_message_time, unread_count)
         */
        handleSidebarUpdate(room) {
            // 사이드바 채팅방 정보 업데이트
            this.sidebarRooms[room.room_id] = {
                lastMessage: room.last_message,
                lastMessageTime: room.last_message_time,
                unreadCount: room.unread_count,
            };

            // DOM 직접 업데이트 (Alpine.js 반응성 외부)
            this.updateSidebarDOM(room);
        },

        /**
         * 사이드바 DOM 업데이트
         * @param {Object} room - 채팅방 정보
         */
        updateSidebarDOM(room) {
            const roomElement = document.querySelector(
                `[data-room-id="${room.room_id}"]`
            );
            if (!roomElement) return;

            // 마지막 메시지 업데이트
            if (room.last_message) {
                const msgElement = roomElement.querySelector('.last-message');
                if (msgElement) {
                    msgElement.textContent = room.last_message;
                }
            }

            // 시간 업데이트
            if (room.last_message_time) {
                const timeElement = roomElement.querySelector('.last-message-time');
                if (timeElement) {
                    timeElement.textContent = formatTime(room.last_message_time);
                }
            }

            // 안읽은 메시지 배지 업데이트
            const badgeElement = roomElement.querySelector('.unread-badge');
            if (badgeElement) {
                if (room.unread_count > 0) {
                    badgeElement.textContent = room.unread_count > 99 ? '99+' : room.unread_count;
                    badgeElement.classList.remove('hidden');
                } else {
                    badgeElement.classList.add('hidden');
                }
            }

            // 현재 선택된 채팅방이면 unread_count를 0으로 처리
            if (room.room_id === this.roomId && room.unread_count > 0) {
                // 이미 해당 방에 있으므로 배지는 숨김
                if (badgeElement) {
                    badgeElement.classList.add('hidden');
                }
            }

            // 채팅방 순서 변경 (새 메시지가 있는 방을 최상단으로)
            this.moveRoomToTop(roomElement);
        },

        /**
         * 채팅방을 목록 최상단으로 이동
         * @param {HTMLElement} roomElement - 이동할 채팅방 요소
         */
        moveRoomToTop(roomElement) {
            // 사이드바 검색 중이면 순서 변경 안 함
            const searchInput = document.getElementById('sidebar-search-input');
            if (searchInput && searchInput.value.trim()) {
                return;
            }

            const roomList = roomElement.parentElement;
            if (!roomList) return;

            // 이미 첫 번째 요소인 경우 이동 불필요
            const firstRoom = roomList.firstElementChild;
            if (firstRoom === roomElement) return;

            // 요소를 최상단으로 이동
            roomList.insertBefore(roomElement, firstRoom);
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
