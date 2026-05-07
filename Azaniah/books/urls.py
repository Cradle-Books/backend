from django.urls import path
from .views import SearchBookView

urlpatterns = [
    path('search/', SearchBookView.as_view(), name = 'search-book'),
]