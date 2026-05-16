from ..models import Book, UserBook
from django.db.models import Avg

def get_trending_books():
    books = Book.objects.all()

    trending_results = []

    for book in books:
        userbooks = UserBook.objects.filter(book=book)

        readers = userbooks.count()
        currently_reading = userbooks.filter(
            status="reading"
        ).count()
        finished = userbooks.filter(
            status="finished"
        ).count()

        avg_rating = userbooks.aggregate(
            avg=Avg("ratings")
        )["avg"] or 0

        score = (
            readers * 2
            + currently_reading * 3
            + finished * 4
            + avg_rating
        )

        trending_results.append({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover": book.cover,
            "score": score,
            "number_of_readers": readers
        })

    trending_results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return {
        "results": trending_results[:10]
    }
