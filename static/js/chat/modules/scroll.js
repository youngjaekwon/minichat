/**
 * 스크롤 및 무한 스크롤 관리 모듈
 */

/**
 * 스크롤 매니저 생성
 * @param {Object} app - chatApp 인스턴스
 * @returns {Object} 스크롤 매니저 객체
 */
export function createScrollManager(app) {
    return {
        observer: null,
        bottomObserver: null,
        scrollThreshold: 150,

        /**
         * 무한 스크롤 설정
         */
        setupInfiniteScroll() {
            this.setupTopSentinel();
        },

        /**
         * 상단 센티널 설정 (스크롤 업)
         */
        setupTopSentinel() {
            if (!app.hasMore) return;

            app.$nextTick(() => {
                const sentinel = app.$refs.loadMoreSentinel;
                if (!sentinel) return;

                this.observer = new IntersectionObserver(
                    (entries) => {
                        entries.forEach((entry) => {
                            if (
                                entry.isIntersecting &&
                                !app.isLoadingMore &&
                                app.hasMore
                            ) {
                                app.messageManager.loadMoreMessages();
                            }
                        });
                    },
                    {
                        root: app.$refs.messagesContainer,
                        rootMargin: '100px 0px 0px 0px',
                        threshold: 0.1,
                    }
                );

                this.observer.observe(sentinel);
            });
        },

        /**
         * 하단 센티널 설정 (스크롤 다운 - 검색 후 사용)
         */
        setupBottomSentinel() {
            if (!app.hasMoreAfter) return;

            if (this.bottomObserver) {
                this.bottomObserver.disconnect();
                this.bottomObserver = null;
            }

            app.$nextTick(() => {
                const sentinel = app.$refs.loadMoreAfterSentinel;
                if (!sentinel) return;

                this.bottomObserver = new IntersectionObserver(
                    (entries) => {
                        entries.forEach((entry) => {
                            if (
                                entry.isIntersecting &&
                                !app.isLoadingMoreAfter &&
                                app.hasMoreAfter
                            ) {
                                app.messageManager.loadMoreMessagesAfter();
                            }
                        });
                    },
                    {
                        root: app.$refs.messagesContainer,
                        rootMargin: '0px 0px 100px 0px',
                        threshold: 0.1,
                    }
                );

                this.bottomObserver.observe(sentinel);
            });
        },

        /**
         * 하단 Observer 연결 해제
         */
        disconnectBottomObserver() {
            if (this.bottomObserver) {
                this.bottomObserver.disconnect();
                this.bottomObserver = null;
            }
        },

        /**
         * 맨 아래로 스크롤
         */
        scrollToBottom() {
            app.$nextTick(() => {
                const container = app.$refs.messagesContainer;
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            });
        },

        /**
         * 스크롤이 맨 아래 근처인지 확인
         * @returns {boolean}
         */
        checkIfNearBottom() {
            const container = app.$refs.messagesContainer;
            if (!container) return true;
            const { scrollTop, scrollHeight, clientHeight } = container;
            return scrollHeight - scrollTop - clientHeight <= this.scrollThreshold;
        },

        /**
         * 스크롤 이벤트 핸들러
         */
        handleScroll() {
            const wasNearBottom = app.isNearBottom;
            app.isNearBottom = this.checkIfNearBottom();

            if (!wasNearBottom && app.isNearBottom) {
                app.showNewMessageToast = false;
                app.newMessageCount = 0;
            }
        },

        /**
         * 토스트 클릭 시 맨 아래로 스크롤
         */
        async scrollToBottomAndHideToast() {
            if (!app.isAtLatest) {
                await app.messageManager.resetToLatest();
            } else {
                this.scrollToBottom();
            }

            app.showNewMessageToast = false;
            app.newMessageCount = 0;
        },

        /**
         * 모든 Observer 정리
         */
        disconnect() {
            if (this.observer) {
                this.observer.disconnect();
                this.observer = null;
            }
            if (this.bottomObserver) {
                this.bottomObserver.disconnect();
                this.bottomObserver = null;
            }
        },
    };
}
