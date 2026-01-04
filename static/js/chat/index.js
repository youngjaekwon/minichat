/**
 * 채팅 앱 진입점
 * Alpine.js에 chatApp 컴포넌트를 등록합니다.
 */

import chatApp from './chatApp.js';

// window 객체에 등록하여 x-data="chatApp(...)"에서 접근 가능하게 함
window.chatApp = chatApp;

// Alpine.js가 이미 로드되었는지 확인
if (window.Alpine) {
    // Alpine이 이미 시작되었으면 바로 등록
    Alpine.data('chatApp', chatApp);
} else {
    // 아직 로드되지 않았으면 이벤트 리스너 등록
    document.addEventListener('alpine:init', () => {
        Alpine.data('chatApp', chatApp);
    });
}
