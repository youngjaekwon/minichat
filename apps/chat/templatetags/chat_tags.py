from datetime import datetime

from django import template

register = template.Library()


@register.filter
def display_name(room, user):
    """대화방의 표시 이름을 반환한다."""
    return room.get_display_name(user)


@register.filter
def korean_time(value: datetime | None) -> str:
    """시간을 한글 오전/오후 형식으로 반환한다."""
    if not value:
        return ""
    hour = value.hour
    minute = value.strftime("%M")
    if hour < 12:
        display_hour = hour if hour else 12
        return f"오전 {display_hour}:{minute}"
    else:
        display_hour = hour - 12 if hour > 12 else 12
        return f"오후 {display_hour}:{minute}"


@register.filter
def get_item(dictionary: dict, key) -> int:
    """딕셔너리에서 키로 값을 가져온다."""
    if not dictionary:
        return 0
    return dictionary.get(key, 0)
