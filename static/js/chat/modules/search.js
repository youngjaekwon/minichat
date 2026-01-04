/**
 * 메시지 검색 모듈
 */

/**
 * 검색 매니저 생성
 * @param {Object} app - chatApp 인스턴스
 * @returns {Object} 검색 매니저 객체
 */
export function createSearchManager(app) {
    return {
        highlightedMessageId: null,

        /**
         * 검색 토글
         */
        toggleSearch() {
            app.isSearchOpen = !app.isSearchOpen;
            if (app.isSearchOpen) {
                app.$nextTick(() => {
                    app.$refs.searchInput?.focus();
                });
            } else {
                this.closeSearch();
            }
        },

        /**
         * 검색 닫기
         */
        closeSearch() {
            app.isSearchOpen = false;
            app.searchQuery = '';
            this.clearSearchResults();
            this.clearHighlight();
        },

        /**
         * 검색 결과 초기화
         */
        clearSearchResults() {
            app.searchResults = [];
            app.searchCurrentIndex = 0;
            app.searchPerformed = false;
        },

        /**
         * 검색 수행
         */
        async performSearch() {
            if (app.searchQuery.length < 2) {
                this.clearSearchResults();
                return;
            }

            app.isSearching = true;
            app.searchPerformed = false;

            try {
                const response = await fetch(
                    `/chat/api/${app.roomId}/messages/search/?q=${encodeURIComponent(app.searchQuery)}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                app.searchResults = data.message_ids || [];
                app.searchCurrentIndex =
                    app.searchResults.length > 0
                        ? app.searchResults.length - 1
                        : 0;
                app.searchPerformed = true;

                if (app.searchResults.length > 0) {
                    this.navigateToResult(app.searchCurrentIndex);
                }
            } catch (error) {
                console.error('Search failed:', error);
                app.showError('검색에 실패했습니다.');
            } finally {
                app.isSearching = false;
            }
        },

        /**
         * 검색 결과 네비게이션
         * @param {number} direction - 1: 다음, -1: 이전
         */
        navigateSearch(direction) {
            if (app.searchResults.length === 0) return;

            let newIndex = app.searchCurrentIndex + direction;

            if (newIndex < 0) {
                newIndex = app.searchResults.length - 1;
            } else if (newIndex >= app.searchResults.length) {
                newIndex = 0;
            }

            app.searchCurrentIndex = newIndex;
            this.navigateToResult(newIndex);
        },

        /**
         * 특정 검색 결과로 이동
         * @param {number} index - 검색 결과 인덱스
         */
        async navigateToResult(index) {
            const messageId = app.searchResults[index];
            if (!messageId) return;

            let messageEl = document.querySelector(
                `[data-message-id="${messageId}"]`
            );

            if (messageEl) {
                this.scrollToMessageAndHighlight(messageId);
            } else {
                await app.messageManager.loadMessagesAround(messageId);
                app.$nextTick(() => {
                    this.scrollToMessageAndHighlight(messageId);
                });
            }
        },

        /**
         * 메시지로 스크롤하고 하이라이트
         * @param {number} messageId - 메시지 ID
         */
        scrollToMessageAndHighlight(messageId) {
            this.clearHighlight();
            this.highlightedMessageId = messageId;

            app.$nextTick(() => {
                const messageEl = document.querySelector(
                    `[data-message-id="${messageId}"]`
                );
                if (messageEl) {
                    messageEl.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                    });

                    const bubbleEl = messageEl.querySelector('.rounded-lg');
                    if (bubbleEl) {
                        bubbleEl.classList.add(
                            'ring-2',
                            'ring-blue-500',
                            'border-blue-500',
                            'animate-pulse'
                        );

                        setTimeout(() => {
                            bubbleEl.classList.remove(
                                'ring-2',
                                'ring-blue-500',
                                'border-blue-500',
                                'animate-pulse'
                            );
                        }, 2000);
                    }
                }
            });
        },

        /**
         * 하이라이트 제거
         */
        clearHighlight() {
            if (this.highlightedMessageId) {
                const prevEl = document.querySelector(
                    `[data-message-id="${this.highlightedMessageId}"]`
                );
                if (prevEl) {
                    const bubbleEl = prevEl.querySelector('.rounded-lg');
                    if (bubbleEl) {
                        bubbleEl.classList.remove(
                            'ring-2',
                            'ring-blue-500',
                            'border-blue-500',
                            'animate-pulse'
                        );
                    }
                }
                this.highlightedMessageId = null;
            }
        },
    };
}
