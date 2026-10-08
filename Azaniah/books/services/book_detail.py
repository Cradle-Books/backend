import requests
import logging
from ..models import Book, UserBook
from .google_books import fetch_google_book

logger = logging.getLogger(__name__)


def get_book_detail(book_id):

    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return None, "not_found"

    number_of_readers = UserBook.objects.filter(book=book).count()

    # ------------------------
    # RETURN CACHED DATA FAST
    # ------------------------
    if book.description and book.average_rating is not None:
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover": book.cover,
            "release_date": book.release_date,
            "genre": book.genre,
            "description": book.description,
            "page_count": book.page_count,
            "average_rating": book.average_rating,
            "number_of_readers": number_of_readers
        }, None

    # ------------------------
    # OPENLIBRARY FETCH
    # ------------------------
    description = None
    page_count = None
    average_rating = book.average_rating

    try:
        url = f"https://openlibrary.org{book.external_id}.json"
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()

            description = data.get("description")
            if isinstance(description, dict):
                description = description.get("value")

            page_count = data.get("number_of_pages")
            if isinstance(page_count, dict):
                page_count = page_count.get("value")

    except requests.RequestException:
        logger.warning("Open Library detail request failed for book %s", book.id, exc_info=True)

    # ------------------------
    # GOOGLE BOOKS FALLBACK
    # ------------------------
    if not description or not page_count or average_rating is None:
        google_data = fetch_google_book(book.title, book.author)

        if google_data:
            if not description:
                description = google_data.get("description")

            if not page_count:
                page_count = google_data.get("page_count")
            if average_rating is None:
                average_rating = google_data.get("average_rating")

    # ------------------------
    # CACHE INTO DB
    # ------------------------
    if description and not book.description:
        book.description = description

    if page_count and not book.page_count:
        book.page_count = page_count
    if average_rating is not None and book.average_rating is None:
        book.average_rating = average_rating

    book.save()

    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "cover": book.cover,
        "release_date": book.release_date,
        "genre": book.genre,
        "description": book.description,
        "page_count": book.page_count,
        "average_rating": book.average_rating,
        "number_of_readers": number_of_readers
    }, None