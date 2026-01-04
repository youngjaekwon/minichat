/**
 * WebSocket 연결 관리 모듈
 */

/**
 * WebSocket 매니저 생성
 * @param {Object} app - chatApp 인스턴스
 * @returns {Object} WebSocket 매니저 객체
 */
export function createWebSocketManager(app) {
    return {
        ws: null,
        reconnectAttempts: 0,
        maxReconnectAttempts: 10,
        reconnectDelay: 1000,
        maxReconnectDelay: 30000,

        /**
         * WebSocket 연결 시작 (채팅방용)
         */
        connect() {
            if (!app.roomId) return;

            app.connectionState =
                this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting';

            const protocol =
                window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            let wsUrl = `${protocol}//${window.location.host}/ws/chat/${app.roomId}/`;

            if (app.lastMessageId) {
                wsUrl += `?last_message_id=${app.lastMessageId}`;
            }

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => this.handleOpen();
            this.ws.onclose = (event) => this.handleClose(event.code);
            this.ws.onerror = (error) => console.error('WebSocket error:', error);
            this.ws.onmessage = (event) =>
                this.handleMessage(JSON.parse(event.data));
        },

        /**
         * 사이드바 전용 WebSocket 연결 (room 없이)
         */
        connectSidebarOnly() {
            const protocol =
                window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
            };
            this.ws.onclose = (event) => this.handleSidebarClose(event.code);
            this.ws.onerror = (error) =>
                console.error('Sidebar WebSocket error:', error);
            this.ws.onmessage = (event) =>
                this.handleMessage(JSON.parse(event.data));
        },

        /**
         * 사이드바 전용 연결 종료 핸들러
         * @param {number} code - 종료 코드
         */
        handleSidebarClose(code) {
            // 인증 오류는 재연결하지 않음
            if ([4001, 4003, 4004].includes(code)) {
                return;
            }

            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                console.error('Max reconnect attempts reached for sidebar');
                return;
            }

            this.reconnectAttempts++;

            // Exponential Backoff with Jitter
            const jitter = Math.random() * 1000;
            const delay = Math.min(
                this.reconnectDelay + jitter,
                this.maxReconnectDelay
            );

            setTimeout(() => this.connectSidebarOnly(), delay);

            this.reconnectDelay = Math.min(
                this.reconnectDelay * 2,
                this.maxReconnectDelay
            );
        },

        /**
         * 연결 성공 핸들러
         */
        handleOpen() {
            app.connectionState = 'connected';
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
        },

        /**
         * 연결 종료 핸들러
         * @param {number} code - 종료 코드
         */
        handleClose(code) {
            app.connectionState = 'disconnected';
            this.handleReconnect(code);
        },

        /**
         * 재연결 처리
         * @param {number} closeCode - 종료 코드
         */
        handleReconnect(closeCode) {
            // 인증 오류는 재연결하지 않음
            if ([4001, 4003, 4004].includes(closeCode)) {
                return;
            }

            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                console.error('Max reconnect attempts reached');
                return;
            }

            this.reconnectAttempts++;
            app.connectionState = 'reconnecting';
            app.reconnectAttempts = this.reconnectAttempts;

            // Exponential Backoff with Jitter
            const jitter = Math.random() * 1000;
            const delay = Math.min(
                this.reconnectDelay + jitter,
                this.maxReconnectDelay
            );

            setTimeout(() => this.connect(), delay);

            // 다음 재연결 시 지연 시간 증가
            this.reconnectDelay = Math.min(
                this.reconnectDelay * 2,
                this.maxReconnectDelay
            );
        },

        /**
         * 메시지 수신 핸들러
         * @param {Object} data - 수신된 메시지 데이터
         */
        handleMessage(data) {
            switch (data.type) {
                case 'chat_message':
                    app.messageManager.handleChatMessage(data.message);
                    break;
                case 'message_ack':
                    app.messageManager.handleMessageAck(data);
                    break;
                case 'read_status':
                    app.messageManager.handleReadStatus(data);
                    break;
                case 'sidebar_update':
                    app.handleSidebarUpdate(data.room);
                    break;
                case 'error':
                    app.showError(data.message);
                    break;
            }
        },

        /**
         * 메시지 전송
         * @param {Object} data - 전송할 데이터
         */
        send(data) {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify(data));
            }
        },

        /**
         * 연결 종료
         */
        disconnect() {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
        },
    };
}
