from ..models import Book, UserBook

def get_recommendations(user):
    #fetch all books in user's library
        user_books = UserBook.objects.filter(user=user)

        #filter books that are currently being read or have been finished
        read_books = user_books.filter(
            status__in=["reading", "want", "finished"]
        )


        user_genres = set() 

        for ub in read_books.select_related("book"):
            genres = ub.book.genre or []
            user_genres.update(genres)

        user_book_ids = user_books.values_list(
            "book_id",
            flat=True
        )

        recommendations = []

        books = Book.objects.exclude(
            id__in=user_book_ids
        )

        for book in books:
            book_genres = set(book.genre or [])

            overlap = len(
                user_genres.intersection(book_genres)
            )

            if overlap > 0:
                recommendations.append({
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "cover": book.cover,
                    "match_score": overlap
                })

        recommendations.sort(
            key=lambda x: x["match_score"],
            reverse=True
        )

        return {
            "message": "Recommendations fetched successfully",
            "results": recommendations[:10]
        }