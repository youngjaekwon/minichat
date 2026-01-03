from django import forms

from apps.chat.models import Message, Room
from apps.users.models import User


class MessageForm(forms.ModelForm):
    """메시지 입력 폼."""

    class Meta:
        model = Message
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "메시지를 입력하세요...",
                    "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                }
            ),
        }

    def save(self, room: Room, sender: User, commit: bool = True) -> Message:
        """메시지를 저장한다."""
        if commit:
            return Message.objects.create_message(
                room=room,
                sender=sender,
                content=self.cleaned_data["content"],
            )
        # commit=False인 경우 (테스트 등에서 사용)
        message = super().save(commit=False)
        message.room = room
        message.sender = sender
        return message
