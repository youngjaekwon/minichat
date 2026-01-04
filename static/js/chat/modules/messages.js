/**
 * 메시지 관리 모듈
 */

import { extractDate, createSeparator } from './dateUtils.js';

/**
 * 메시지 매니저 생성
 * @param {Object} app - chatApp 인스턴스
 * @returns {Object} 메시지 매니저 객체
 */
export function createMessageManager(app) {
    return {
        pendingMessages: {},

        /**
         * 초기 메시지 로드
         */
        async loadInitialMessages() {
            app.isInitialLoading = true;

            try {
                const response = await fetch(
                    `/chat/api/${app.roomId}/messages/`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.messages && data.messages.length > 0) {
                    app.oldMessages = this.processInitialMessages(data.messages);
                    app.hasMore = data.has_more_before;
                    app.oldestMessageId = data.next_cursor_before;

                    const lastMsg = data.messages[data.messages.length - 1];
                    app.lastMessageId = lastMsg.id;
                    app.lastDate = extractDate(lastMsg.created_at);
                }

                app.$nextTick(() => app.scrollManager.scrollToBottom());
            } catch (error) {
                console.error('Failed to load initial messages:', error);
                app.showError('메시지를 불러오는데 실패했습니다.');
            } finally {
                app.isInitialLoading = false;
            }
        },

        /**
         * 초기 메시지 처리 (날짜 구분선 포함)
         * @param {Array} messages - 메시지 배열
         * @returns {Array} 처리된 메시지 배열
         */
        processInitialMessages(messages) {
            const result = [];
            let prevDate = null;

            for (const msg of messages) {
                const msgDate = extractDate(msg.created_at);

                if (msgDate !== prevDate) {
                    result.push(createSeparator(msgDate));
                    prevDate = msgDate;
                }

                result.push({
                    ...msg,
                    type: 'message',
                });
            }

            return result;
        },

        /**
         * 이전 메시지 로드 (스크롤 업)
         */
        async loadMoreMessages() {
            if (app.isLoadingMore || !app.hasMore || !app.oldestMessageId)
                return;

            app.isLoadingMore = true;
            const container = app.$refs.messagesContainer;
            const scrollHeightBefore = container.scrollHeight;
            const scrollTopBefore = container.scrollTop;

            try {
                const response = await fetch(
                    `/chat/api/${app.roomId}/messages/?direction=before&cursor=${app.oldestMessageId}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.messages && data.messages.length > 0) {
                    const processedMessages = this.processOldMessages(
                        data.messages
                    );
                    app.oldMessages = [...processedMessages, ...app.oldMessages];

                    app.oldestMessageId = data.next_cursor_before;
                    app.hasMore = data.has_more_before;

                    app.$nextTick(() => {
                        const scrollHeightAfter = container.scrollHeight;
                        container.scrollTop =
                            scrollTopBefore +
                            (scrollHeightAfter - scrollHeightBefore);
                    });
                }
            } catch (error) {
                console.error('Failed to load more messages:', error);
                app.showError('이전 메시지를 불러오는데 실패했습니다.');
            } finally {
                app.isLoadingMore = false;
            }
        },

        /**
         * 이후 메시지 로드 (스크롤 다운)
         */
        async loadMoreMessagesAfter() {
            if (
                app.isLoadingMoreAfter ||
                !app.hasMoreAfter ||
                !app.newestMessageId
            )
                return;

            app.isLoadingMoreAfter = true;

            try {
                const response = await fetch(
                    `/chat/api/${app.roomId}/messages/?direction=after&cursor=${app.newestMessageId}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.messages && data.messages.length > 0) {
                    const processedMessages = this.processNewMessages(
                        data.messages
                    );
                    app.messages = [...app.messages, ...processedMessages];

                    app.newestMessageId = data.next_cursor_after;
                    app.hasMoreAfter = data.has_more_after;

                    if (!app.hasMoreAfter) {
                        app.isAtLatest = true;
                        app.scrollManager.disconnectBottomObserver();
                    }
                }
            } catch (error) {
                console.error('Failed to load more messages after:', error);
                app.showError('이후 메시지를 불러오는데 실패했습니다.');
            } finally {
                app.isLoadingMoreAfter = false;
            }
        },

        /**
         * 메시지 주변 로드 (검색 결과 이동용)
         * @param {number} messageId - 메시지 ID
         */
        async loadMessagesAround(messageId) {
            try {
                const response = await fetch(
                    `/chat/api/${app.roomId}/messages/?direction=around&cursor=${messageId}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.messages && data.messages.length > 0) {
                    app.oldMessages = [];
                    app.messages = [];

                    const processedMessages = this.processInitialMessages(
                        data.messages
                    );
                    app.oldMessages = processedMessages;

                    app.hasMore = data.has_more_before;
                    app.hasMoreAfter = data.has_more_after;
                    app.oldestMessageId = data.next_cursor_before;
                    app.newestMessageId = data.next_cursor_after;

                    app.isAtLatest = !data.has_more_after;

                    if (app.hasMoreAfter) {
                        app.$nextTick(() => {
                            app.scrollManager.setupBottomSentinel();
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to load messages around:', error);
                app.showError('메시지를 불러오는데 실패했습니다.');
            }
        },

        /**
         * 이전 메시지 처리 (날짜 구분선 포함)
         * @param {Array} messages - 메시지 배열
         * @returns {Array} 처리된 메시지 배열
         */
        processOldMessages(messages) {
            const result = [];

            const existingFirstMsg = app.oldMessages.find(
                (m) => m.type !== 'separator'
            );
            const existingFirstDate = existingFirstMsg
                ? extractDate(existingFirstMsg.created_at)
                : app.firstDate;

            const lastMsgDate =
                messages.length > 0
                    ? extractDate(messages[messages.length - 1].created_at)
                    : null;

            let prevDate = null;

            for (let i = 0; i < messages.length; i++) {
                const msg = messages[i];
                const msgDate = extractDate(msg.created_at);

                if (msgDate !== prevDate) {
                    const existsInDOM = document.querySelector(
                        `.date-separator[data-date="${msgDate}"]`
                    );
                    const existsInOld = app.oldMessages.some(
                        (m) => m.type === 'separator' && m.date === msgDate
                    );
                    const skipForExisting =
                        msgDate === lastMsgDate &&
                        msgDate === existingFirstDate;

                    if (!existsInDOM && !existsInOld && !skipForExisting) {
                        result.push(createSeparator(msgDate));
                    }
                    prevDate = msgDate;
                }

                result.push({
                    ...msg,
                    type: 'message',
                });
            }

            return result;
        },

        /**
         * 이후 메시지 처리 (날짜 구분선 포함)
         * @param {Array} messages - 메시지 배열
         * @returns {Array} 처리된 메시지 배열
         */
        processNewMessages(messages) {
            const result = [];

            const existingLastMsg =
                app.messages.length > 0
                    ? app.messages
                          .filter((m) => m.type !== 'separator')
                          .slice(-1)[0]
                    : app.oldMessages
                          .filter((m) => m.type !== 'separator')
                          .slice(-1)[0];
            let prevDate = existingLastMsg
                ? extractDate(existingLastMsg.created_at)
                : app.lastDate;

            for (let i = 0; i < messages.length; i++) {
                const msg = messages[i];
                const msgDate = extractDate(msg.created_at);

                if (msgDate !== prevDate) {
                    const existsInDOM = document.querySelector(
                        `.date-separator[data-date="${msgDate}"]`
                    );
                    const existsInMessages = app.messages.some(
                        (m) => m.type === 'separator' && m.date === msgDate
                    );
                    const existsInOld = app.oldMessages.some(
                        (m) => m.type === 'separator' && m.date === msgDate
                    );

                    if (!existsInDOM && !existsInMessages && !existsInOld) {
                        result.push(createSeparator(msgDate));
                    }
                    prevDate = msgDate;
                }

                result.push({
                    ...msg,
                    type: 'message',
                });
            }

            if (result.length > 0) {
                const lastMsg = result
                    .filter((m) => m.type !== 'separator')
                    .slice(-1)[0];
                if (lastMsg) {
                    app.lastDate = extractDate(lastMsg.created_at);
                }
            }

            return result;
        },

        /**
         * 실시간 메시지 수신 처리
         * @param {Object} message - 수신된 메시지
         */
        handleChatMessage(message) {
            const existingInNew = app.messages.find((m) => m.id === message.id);
            const existingInDOM = document.querySelector(
                `[data-message-id="${message.id}"]`
            );

            if (existingInNew || existingInDOM) {
                return;
            }

            if (!app.isAtLatest) {
                app.newMessageCount++;
                app.showNewMessageToast = true;
                return;
            }

            const messageDate = extractDate(message.created_at);
            if (messageDate && messageDate !== app.lastDate) {
                const separatorExists = app.messages.some(
                    (m) => m.type === 'separator' && m.date === messageDate
                );
                const domSeparatorExists = document.querySelector(
                    `.date-separator[data-date="${messageDate}"]`
                );

                if (!separatorExists && !domSeparatorExists) {
                    app.messages.push(createSeparator(messageDate));
                }
                app.lastDate = messageDate;
            }

            if (message.sender_id === app.userId) {
                const pending = Object.values(this.pendingMessages).find(
                    (p) =>
                        p.content === message.content && p.status === 'sending'
                );
                if (pending) {
                    const index = app.messages.findIndex(
                        (m) => m.clientId === pending.clientId
                    );
                    if (index !== -1) {
                        app.messages[index] = {
                            ...message,
                            status: 'sent',
                        };
                        delete this.pendingMessages[pending.clientId];
                        app.lastMessageId = message.id;
                        app.scrollManager.scrollToBottom();
                        return;
                    }
                }
            }

            const shouldPreserveScroll =
                !app.isNearBottom && message.sender_id !== app.userId;

            app.messages.push({
                ...message,
                status: 'received',
            });
            app.lastMessageId = message.id;

            if (shouldPreserveScroll) {
                app.newMessageCount++;
                app.showNewMessageToast = true;
            } else {
                app.$nextTick(() => {
                    app.scrollManager.scrollToBottom();
                });

                // 다른 사용자의 메시지이고, 스크롤이 하단 근처인 경우 즉시 읽음 처리 요청
                if (message.sender_id !== app.userId) {
                    this.sendMarkAsRead([message.id]);
                }
            }
        },

        /**
         * 메시지 읽음 처리 요청 전송
         * @param {Array<number>} messageIds - 읽음 처리할 메시지 ID 배열
         */
        sendMarkAsRead(messageIds) {
            if (
                !messageIds ||
                messageIds.length === 0 ||
                app.connectionState !== 'connected'
            ) {
                return;
            }

            app.wsManager.send({
                type: 'mark_as_read',
                message_ids: messageIds,
            });
        },

        /**
         * 메시지 ACK 처리
         * @param {Object} data - ACK 데이터
         */
        handleMessageAck(data) {
            const pending = this.pendingMessages[data.client_id];
            if (pending) {
                const index = app.messages.findIndex(
                    (m) => m.clientId === data.client_id
                );
                if (index !== -1) {
                    app.messages[index].id = data.message_id;
                    app.messages[index].status = 'sent';
                }
                delete this.pendingMessages[data.client_id];
            }
        },

        /**
         * 읽음 상태 업데이트 처리
         * @param {Object} data - 읽음 상태 데이터 (room_id, message_ids, reader_id)
         */
        handleReadStatus(data) {
            // 현재 채팅방이 아니면 무시
            if (data.room_id !== app.roomId) {
                return;
            }

            const messageIds = new Set(data.message_ids);

            // oldMessages에서 unread_count 감소
            for (const msg of app.oldMessages) {
                if (msg.type === 'message' && messageIds.has(msg.id)) {
                    if (msg.unread_count > 0) {
                        msg.unread_count--;
                    }
                }
            }

            // messages에서 unread_count 감소
            for (const msg of app.messages) {
                if (msg.type !== 'separator' && messageIds.has(msg.id)) {
                    if (msg.unread_count > 0) {
                        msg.unread_count--;
                    }
                }
            }
        },

        /**
         * 메시지 전송
         */
        sendMessage() {
            const content = app.messageInput.trim();
            if (!content || app.connectionState !== 'connected') return;

            if (content.length > app.maxMessageLength) {
                app.showError(
                    `메시지는 ${app.maxMessageLength.toLocaleString()}자를 초과할 수 없습니다.`
                );
                return;
            }

            const clientId = crypto.randomUUID();

            app.wsManager.send({
                type: 'chat_message',
                content: content,
                client_id: clientId,
            });

            const now = new Date().toISOString();

            const messageDate = extractDate(now);
            if (messageDate && messageDate !== app.lastDate) {
                const separatorExists = app.messages.some(
                    (m) => m.type === 'separator' && m.date === messageDate
                );
                const domSeparatorExists = document.querySelector(
                    `.date-separator[data-date="${messageDate}"]`
                );

                if (!separatorExists && !domSeparatorExists) {
                    app.messages.push(createSeparator(messageDate));
                }
                app.lastDate = messageDate;
            }

            const pendingMessage = {
                clientId: clientId,
                content: content,
                sender_id: app.userId,
                sender_name: app.userName,
                created_at: now,
                status: 'sending',
                unread_count: app.participantCount - 1, // 발신자 제외
            };

            app.messages.push(pendingMessage);
            this.pendingMessages[clientId] = pendingMessage;

            app.messageInput = '';

            app.scrollManager.scrollToBottom();
        },

        /**
         * 최신 상태로 리셋
         */
        async resetToLatest() {
            app.oldMessages = [];
            app.messages = [];

            app.hasMoreAfter = false;
            app.newestMessageId = null;
            app.scrollManager.disconnectBottomObserver();

            await this.loadInitialMessages();

            app.isAtLatest = true;

            app.scrollManager.setupInfiniteScroll();
        },
    };
}
