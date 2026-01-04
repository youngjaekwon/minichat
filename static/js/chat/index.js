/**
 * 채팅 앱 진입점
 * Alpine.js에 chatApp 컴포넌트를 등록합니다.
 */

import chatApp from './chatApp.js';

// window 객체에 등록하여 x-data="chatApp(...)"에서 접근 가능하게 함
window.chatApp = chatApp;

// Alpine.js 초기화 이벤트에서 컴포넌트 등록 (Alpine.data 방식도 지원)
document.addEventListener('alpine:init', () => {
    Alpine.data('chatApp', chatApp);
});
