/**
 * 날짜/시간 유틸리티 모듈
 */

/**
 * ISO 8601 문자열을 한국어 시간 형식으로 변환
 * @param {string} isoString - ISO 8601 형식의 날짜 문자열
 * @returns {string} "오전/오후 H:MM" 형식의 시간 문자열
 */
export function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const period = hours < 12 ? '오전' : '오후';
    const displayHours = hours % 12 || 12;
    return `${period} ${displayHours}:${minutes}`;
}

/**
 * ISO 8601 문자열에서 날짜 부분 추출
 * @param {string} isoString - ISO 8601 형식의 날짜 문자열
 * @returns {string|null} "YYYY-MM-DD" 형식의 날짜 문자열
 */
export function extractDate(isoString) {
    if (!isoString) return null;
    const date = new Date(isoString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * 날짜를 표시 형식으로 변환
 * @param {string} dateStr - "YYYY-MM-DD" 형식의 날짜 문자열
 * @returns {string} "Y. m. d" 형식의 표시용 날짜 문자열
 */
export function formatDateDisplay(dateStr) {
    if (!dateStr) return '';
    const [year, month, day] = dateStr.split('-');
    return `${year}. ${month}. ${day}`;
}

/**
 * 날짜 구분선 객체 생성
 * @param {string} dateStr - "YYYY-MM-DD" 형식의 날짜 문자열
 * @returns {Object} 날짜 구분선 객체
 */
export function createSeparator(dateStr) {
    return {
        type: 'separator',
        date: dateStr,
        displayDate: formatDateDisplay(dateStr),
    };
}

/**
 * 채팅방 목록용 시간 포맷팅
 * 오늘이면 시간(오전/오후), 아니면 날짜(YYYY.MM.DD)를 반환
 * @param {string} isoString - ISO 8601 형식의 날짜 문자열
 * @param {boolean} isToday - 오늘 날짜 여부
 * @returns {string} 포맷팅된 시간 또는 날짜 문자열
 */
export function formatRoomTime(isoString, isToday) {
    if (!isoString) return '';

    if (isToday) {
        return formatTime(isoString);
    }

    const date = new Date(isoString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
}
