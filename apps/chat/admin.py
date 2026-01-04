from django.contrib import admin

from apps.chat.models import Message, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_direct",
        "participant_count",
        "created_by",
        "created_at",
    )
    list_select_related = ("created_by",)
    list_filter = ("is_direct", "created_at")
    search_fields = ("name",)
    filter_horizontal = ("participants",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "sender",
        "content_preview",
        "created_at",
    )
    list_select_related = ("room", "sender")
    list_filter = ("created_at",)
    search_fields = ("content",)
    raw_id_fields = ("room", "sender")
    readonly_fields = ("created_at",)

    @admin.display(description="내용")
    def content_preview(self, obj: Message) -> str:
        return obj.get_preview(max_length=30)
