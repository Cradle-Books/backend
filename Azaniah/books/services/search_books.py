import requests
from ..models import Book
from django.db.models import Q
from .google_books import fetch_google_book


def search_books(query, page, page_size):
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
            return {
                "source": "db",
                "results": results
            }

        # 2. CALL OPEN LIBRARY ONLY IF PAGE IS INCOMPLETE
        needed = page_size - len(results)
        
        url = f"https://openlibrary.org/search.json?q={query}&page={page}&limit={page_size}"
        #search for the book title in the open library api if there are not enough results in the database
        response = requests.get(url)

        if response.status_code != 200:
            return {
                "error": "API was unable to process the request"
            }
        
        data = response.json()
        

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
                
            author = item.get("author_name", ["Unknown Author"])[0]
            cover = f"https://covers.openlibrary.org/b/id/{item.get('cover_i')}-M.jpg"
            google_data = None
            google_books_id = None

            if not genres or not item.get("cover_i"):
                #if genres or cover is None, we will attempt to fetch additional details from the Google Books API such as description, page count using the title and author information. This is done to enhance our book data with more comprehensive information, such as genre and cover image, which may not be fully available from the Open Library API. By leveraging the Google Books API, we can provide a richer user experience with more detailed book information.
                google_data = fetch_google_book(title, author)

                if google_data:
                    if not genres:
                        genres = google_data.get("genre", [])

                    if not item.get("cover_i"):
                        cover = google_data.get("cover")

                    google_books_id = google_data.get("google_books_id")
                else:
                    google_books_id = None

            book_data = {
                "external_id": item["key"], #not using .get() here because we want to ensure that this key is always present, as it's crucial for identifying the book in our database. If it's missing, we want the code to raise an error rather than silently failing.
                "google_books_id": google_books_id,
                "title": title, 
                "author": item.get("author_name", ["Unknown Author"])[0],
                "release_date": item.get("first_publish_year"),
                "cover": cover,
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
        
        return {
            "source": "mixed",
            "results": combined
        }