from django.urls import path

from apps.chat import apis, views

app_name = "chat"

urlpatterns = [
    path("", views.RoomListView.as_view(), name="room_list"),
    path("new/", views.NewConversationView.as_view(), name="new_conversation"),
    path("<int:pk>/", views.RoomDetailView.as_view(), name="room_detail"),
    path(
        "api/rooms/",
        apis.RoomListAPIView.as_view(),
        name="api_rooms",
    ),
    path(
        "api/rooms/search/",
        apis.RoomSearchAPIView.as_view(),
        name="api_rooms_search",
    ),
    path(
        "api/<int:room_id>/messages/",
        apis.MessageListAPIView.as_view(),
        name="api_messages",
    ),
    path(
        "api/<int:room_id>/messages/search/",
        apis.MessageSearchAPIView.as_view(),
        name="api_messages_search",
    ),
]
