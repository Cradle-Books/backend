import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from django.db.models import Q
from ..models import Book
from .google_books import fetch_google_book

logger = logging.getLogger(__name__)


def _enrich_cached_books(books):
    incomplete_books = [
        book
        for book in books
        if not book.description or book.average_rating is None
    ]
    if not incomplete_books:
        return

    with ThreadPoolExecutor(max_workers=min(4, len(incomplete_books))) as executor:
        lookups = executor.map(
            lambda book: (book, fetch_google_book(book.title, book.author)),
            incomplete_books,
        )
        for book, google_data in lookups:
            if not google_data:
                continue

            changed_fields = []
            if not book.description and google_data.get("description"):
                book.description = google_data["description"]
                changed_fields.append("description")
            if book.average_rating is None and google_data.get("average_rating") is not None:
                book.average_rating = google_data["average_rating"]
                changed_fields.append("average_rating")
            if changed_fields:
                book.save(update_fields=changed_fields)


def search_books(query, page, page_size):
    start = (page - 1) * page_size
    end = page * page_size

    db_books = Book.objects.filter(Q(title__icontains=query)).order_by("id")
    db_results = list(db_books[start:end])
    _enrich_cached_books(db_results)
    results = [
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover": book.cover,
            "release_date": book.release_date,
            "genre": book.genre,
            "work_id": book.external_id,
            "description": book.description,
            "average_rating": book.average_rating,
        }
        for book in db_results
    ]

    if len(db_results) == page_size:
        return {"source": "db", "results": results}
    needed = page_size - len(results)
    try:
        response = requests.get(
            "https://openlibrary.org/search.json",
            params={"q": query, "page": page, "limit": page_size},
            timeout=10,
        )
    except requests.RequestException:
        return {"error": "Open Library search request failed"}

    if response.status_code != 200:
        return {"error": "API was unable to process the request"}

    data = response.json()
    docs = sorted(
        data.get("docs", []),
        key=lambda item: item.get("edition_count", 0),
        reverse=True,
    )
    clean_books = []
    existing_ids = {book.id for book in db_results}

    for item in docs:
        if len(clean_books) >= needed:
            break
        if not item.get("title") or not item.get("key"):
            continue

        title = item["title"]
        if "summary" in title.lower():
            continue

        work_id = item["key"]
        description = None
        genres = item.get("subject", [])[:3]

        # The search document's key is a work ID; fetch that work's metadata.
        try:
            details_response = requests.get(
                f"https://openlibrary.org{work_id}.json",
                timeout=10,
            )
            if details_response.status_code == 200:
                details_data = details_response.json()
                raw_description = details_data.get("description")
                if isinstance(raw_description, dict):
                    description = raw_description.get("value")
                elif isinstance(raw_description, str):
                    description = raw_description
                if not genres:
                    genres = details_data.get("subjects", [])[:3]
        except requests.RequestException:
            logger.warning("Open Library work lookup failed for %s", work_id, exc_info=True)

        author = item.get("author_name", ["Unknown Author"])[0]
        cover_id = item.get("cover_i")
        cover = (
            f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            if cover_id
            else None
        )
        average_rating = item.get("ratings_average")
        google_data = None
        google_books_id = None

        if not description or not genres or not cover or average_rating is None:
            google_data = fetch_google_book(title, author)
            if google_data:
                description = description or google_data.get("description")
                genres = genres or google_data.get("genre", [])
                cover = cover or google_data.get("cover")
                google_books_id = google_data.get("google_books_id")
                average_rating = average_rating or google_data.get("average_rating")

        book_data = {
            "external_id": work_id,
            "google_books_id": google_books_id,
            "title": title,
            "author": author,
            "release_date": item.get("first_publish_year"),
            "cover": cover,
            "genre": genres,
            "description": description or "",
            "average_rating": average_rating,
        }

        book_obj, created = Book.objects.get_or_create(
            external_id=work_id,
            defaults=book_data,
        )

        if not created:
            changed_fields = []
            for field in (
                "description",
                "cover",
                "genre",
                "google_books_id",
                "average_rating",
            ):
                value = book_data[field]
                if value and not getattr(book_obj, field):
                    setattr(book_obj, field, value)
                    changed_fields.append(field)
            if changed_fields:
                book_obj.save(update_fields=changed_fields)

        if book_obj.id in existing_ids:
            continue

        clean_books.append(
            {
                "id": book_obj.id,
                "title": book_obj.title,
                "author": book_obj.author,
                "cover": book_obj.cover,
                "release_date": book_obj.release_date,
                "genre": book_obj.genre,
                "description": book_obj.description,
                "work_id": book_obj.external_id,
                "average_rating": book_obj.average_rating,
            }
        )

    return {"source": "mixed", "results": results + clean_books}
