from django.urls import path
from .views import SearchBookView, AddToLibraryView

urlpatterns = [
    path('search/', SearchBookView.as_view(), name = 'search-book'),
    path('library/', AddToLibraryView.as_view(), name = 'add-to-library')
]