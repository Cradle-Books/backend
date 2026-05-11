from django.urls import path
from .views import SearchBookView, AddToLibraryView, FetchLibraryView, UpdateLibraryView

urlpatterns = [
    path('search/', SearchBookView.as_view(), name = 'search-book'),
    path('library/', AddToLibraryView.as_view(), name = 'add-to-library'),
    path('library/fetch/', FetchLibraryView.as_view(), name = 'fetch-library'),
    path('library/update/<int:userbook_id>/', UpdateLibraryView.as_view(), name = 'update-library')
]