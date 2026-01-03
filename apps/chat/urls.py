from django.urls import path

from apps.chat import views

app_name = "chat"

urlpatterns = [
    path("", views.RoomListView.as_view(), name="room_list"),
    path("new/", views.NewConversationView.as_view(), name="new_conversation"),
    path("<int:pk>/", views.RoomDetailView.as_view(), name="room_detail"),
    path("<int:pk>/send/", views.SendMessageView.as_view(), name="send_message"),
]
