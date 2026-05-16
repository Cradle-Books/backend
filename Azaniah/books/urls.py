from django.urls import path
from .views import SearchBookView, AddToLibraryView, FetchLibraryView, UpdateLibraryView, DeleteUserBookView, BookDetailView, UserProfileView, RecommendationView, TrendingView

urlpatterns = [
    path('search/', SearchBookView.as_view(), name = 'search-book'),
    path('library/', AddToLibraryView.as_view(), name = 'add-to-library'),
    path('library/fetch/', FetchLibraryView.as_view(), name = 'fetch-library'),
    path('library/update/<int:userbook_id>/', UpdateLibraryView.as_view(), name = 'update-library'),
    path('library/delete/<int:userbook_id>/', DeleteUserBookView.as_view(), name = 'remove-from-library'),
    path('book/<int:book_id>/', BookDetailView.as_view(), name = 'book-detail'),
    path('profile/', UserProfileView.as_view(), name = 'user-profile'),
    path('trending/', TrendingView.as_view(), name = 'trending'),
    path('recommendations/', RecommendationView.as_view(), name = 'recommendations')
]