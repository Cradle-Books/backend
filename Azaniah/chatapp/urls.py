from django.urls import path
from .views import CurrentChatUserView

urlpatterns = [
    path("me/", CurrentChatUserView.as_view(), name = "chat-current-user"),
]