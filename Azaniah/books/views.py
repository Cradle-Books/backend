from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from .serializers import BookSerializer, UserBookSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging
import requests
from .models import Book, UserBook
from django.conf import settings
from .services.search_books import search_books
from .services.book_detail import get_book_detail
from .services.userbook_profile import get_userbook_profile
from .services.trending_books import get_trending_books
from .services.recommendations import get_recommendations
from django.utils import timezone

# Create your views here.

class SearchBookView(APIView):
    """
    Book search endpoint combining database and Open Library API results.
    
    Architecture Pattern (see docs/BACKEND.md - Pattern 8):
    - search_books() service returns a dictionary, NOT a Response object
    - View handles all HTTP response creation and error handling
    - This allows service functions to be reused across different contexts
    
    Example service returns:
    - Success: {"source": "db|mixed", "results": [...]}
    - Error: {"error": "message"}
    
    View's responsibility: wrap service output + handle HTTP status codes
    """

    permission_classes = [] 
    authentication_classes = []

    def get(self, request):
        query = request.GET.get('q')
        page = int(request.GET.get('page'))
        page_size = int(request.GET.get("page_size", 12))


        #check if the query(or what is to be searched for) is provided
        if not query:
            return Response({
                "message": "The Title of the book is required"
            }, status = status.HTTP_400_BAD_REQUEST)
        
        # Call service function (returns dict, never Response)
        result = search_books(query, page, page_size)

        # Check if there was an error
        if "error" in result:
            return Response({
                "message": result["error"]
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # View wraps service output in Response with HTTP metadata
        return Response({
            "message": "Search completed successfully",
            "source": result["source"],
            "page": page,
            "page_size": page_size,
            "results": result["results"]
        })


class AddToLibraryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserBookSerializer(data=request.data, context={'request': request}) #context is needed for the serializer in order to relate the existence of the user to the book being added to the library. This allows us to check if the book already exists in the user's library and to associate the new UserBook entry with the correct user when saving it to the database.

        if serializer.is_valid():
            #if book doesn't exist user's library, and user to book relationship is valid and doesn't exist, then the book is added to the user's library.
            user_book = serializer.save()

            return Response({
                "message": "Book added to library successfully",
                "data": UserBookSerializer(user_book, context={'request': request}).data #can also just be written as serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FetchLibraryView(APIView):
    #authentication and permission classes are meant to be directly nested in the class function.
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_books = UserBook.objects.filter(
            user = request.user
        ).order_by("-created_at")

        serializer = UserBookSerializer(user_books, many = True) #many = True because user_books is a queryset that can contain multiple UserBook instances, and we want to serialize all of them into a list of dictionaries. If we set many = False, the serializer would expect a single UserBook instance and would raise an error when it receives a queryset instead.

        return Response({
            "message": "Library fetched successfully",
            "amount": user_books.count(),
            "books": serializer.data 
        }, status = status.HTTP_200_OK)

class UpdateLibraryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, userbook_id): #patch allows us to update only specific fields of the UserBook instance, rather than requiring all fields to be provided as in a PUT request. This is useful for updating the reading status or rating without needing to resend all the book information.
        #where userbook_id is the id of the unique user to book relationship.

        try:
            #this fetches userbook object that matches the provided userbook_id that we want to update.
            user_book = UserBook.objects.get(id=userbook_id, user=request.user)

        except UserBook.DoesNotExist:
            #checks if the user to book relationship exists.
            return Response({
                "message": "Book not found in your library"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UserBookSerializer(user_book, data=request.data, partial=True, context={'request': request})
        status_changed = (
            "status" in request.data and request.data["status"] != user_book.status
        )

        if serializer.is_valid(): 
            updated_book = serializer.save()
            if status_changed:
                updated_book.status_changed_at = timezone.now()
                updated_book.save(update_fields = ["status_changed_at"])

            return Response({
                "message": "Book updated successfully",
                "data": UserBookSerializer(updated_book, context={'request': request}).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteUserBookView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, userbook_id):
        try:
            user_book = UserBook.objects.get(id=userbook_id, user=request.user) #fetches unique user - book relationship using userbook_id.

        except UserBook.DoesNotExist:
            return Response({
                "message": "Book not found in your library"
            }, status=status.HTTP_404_NOT_FOUND)

        user_book.delete() #deletes unique user - book relationship from library.

        return Response({
            "message": "Book removed from library successfully"
        }, status=status.HTTP_204_NO_CONTENT)

class BookDetailView(APIView):
    permission_classes = [] 
    authentication_classes = []

    def get(self, request, book_id):

        data, error = get_book_detail(book_id)

        if error == "not_found":
            return Response(
                {"message": "Book not found"},
                status=404
            )

        return Response(data, status = status.HTTP_200_OK)

    
class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        profile_data = get_userbook_profile(user)

        return Response(profile_data, status = status.HTTP_200_OK)

class TrendingView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):

        data = get_trending_books()

        return Response(data, status = status.HTTP_200_OK)

        
class RecommendationView(APIView):
    #only authenticated users can get recommendations
    permission_classes = [IsAuthenticated]

    def get(self, request):
        #fetch user
        user = request.user

        data = get_recommendations(user)

        return Response(data, status = status.HTTP_200_OK)
