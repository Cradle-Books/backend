from django.shortcuts import render
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework import status
from .serializers import BookSerializer, UserBookSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging
import requests
from .models import Book, UserBook

# Create your views here.
class SearchBookView(APIView):

    permission_classes = [] 
    authentication_classes = []

    def get(self, request):
        query = request.GET.get('q')
        page = int(request.GET.get('page'))
        page_size = int(request.GET.get("page_size", 10))


        #check if the query(or what is to be searched for) is provided
        if not query:
            return Response({
                "message": "The Title of the book is required"
            }, status = status.HTTP_400_BAD_REQUEST)
        
        start = (page - 1) * page_size
        end = page * page_size
        
        #check database first for the book title
        db_books = Book.objects.filter(Q(title__icontains = query)).order_by("id")
        db_results = list(db_books[start:end])

        results = [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "cover": book.cover,
                "release_date": book.release_date,
                "genre": book.genre
            }
            for book in db_results
        ]

        # If DB already fills this page completely, return immediately
        if len(results) == page_size:
            return Response({
                "source": "db",
                "page": page,
                "page_size": page_size,
                "results": results
            })

        # 2. CALL OPEN LIBRARY ONLY IF PAGE IS INCOMPLETE
        needed = page_size - len(results)
        
        url = f"https://openlibrary.org/search.json?q={query}&page={page}&limit={page_size}"
        #search for the book title in the open library api if there are not enough results in the database
        response = requests.get(url)

        if response.status_code != 200:
            return Response({
                "message": "API was unable to process the request"
            }, status = status.HTTP_503_SERVICE_UNAVAILABLE)
        
        data = response.json()
        print(data.get("docs", [])[:3])

        #sort the results by edition count in descending order to get the most popular books first
        docs = sorted( 
            data.get("docs", []), 
            key=lambda x: x.get("edition_count", 0), 
            reverse=True
        ) 
        
        #defining a list to hold the cleaned and formatted book data fetched from the API
        clean_books = []

        existing_ids = {book.id for book in db_results}

        for item in docs:
            if len(clean_books) >= needed:
                break

            if not item.get("title") or not item.get("key"):
                continue

            title = item["title"] #recall, .get is accompanied by () and [] allows us to use without .get. we are using [] here because we want to ensure that the title is always present, as it's crucial for identifying the book in our database. If it's missing, we want the code to raise an error rather than silently failing.

            if "summary" in title.lower():
                continue

            #dictionary for results saved to Book model database
            genres = item.get("subject", [])[:3]

            if not genres:
                details_url = f"https://openlibrary.org{item['key']}.json"
                details_response = requests.get(details_url)

                if details_response.status_code == 200:
                    details_data = details_response.json()
                    genres = details_data.get("subjects", [])[:3] 

            book_data = {
                "external_id": item["key"], #not using .get() here because we want to ensure that this key is always present, as it's crucial for identifying the book in our database. If it's missing, we want the code to raise an error rather than silently failing.
                "title": title, 
                "author": item.get("author_name", ["Unknown Author"])[0],
                "release_date": item.get("first_publish_year"),
                "cover": f"https://covers.openlibrary.org/b/id/{item.get('cover_i')}-M.jpg",
                "genre": genres
                
            #[]square brackets make conditions a MUST, while .get() is more flexible and allows for missing data without breaking the code. .get() returns None if the key is not found, while [] raises a KeyError.
            }

            #django object is created after saving book_data dictionary to the database
            book_obj, created = Book.objects.get_or_create( 
                external_id=book_data["external_id"],
                defaults=book_data
            )

            if book_obj.id in existing_ids:
                continue

            #display for API results
            clean_books.append({
                "id": book_obj.id, #id instead of external_id for frontend use
                "title": book_obj.title,
                "author": book_obj.author,
                "cover": book_obj.cover,
                "release_date": book_obj.release_date,
                "genre": book_obj.genre
            })
             
        
        # 🔄 6. COMBINE DB + API RESULTS
        combined = results + clean_books 
        
        return Response({
            "source": "mixed",
            "page": page,
            "page_size": page_size,
            "results": combined
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

        if serializer.is_valid():
            updated_book = serializer.save()
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