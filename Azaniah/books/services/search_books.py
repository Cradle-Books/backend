import requests
import logging
from django.db.models import Q
from ..models import Book
from django.conf import settings

logger = logging.getLogger(__name__)


def search_books(query, page, page_size):
    start = (page - 1) * page_size
    end = page * page_size

    db_books = Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query)).order_by("id")
    db_results = list(db_books[start:end])
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
            f"{settings.OPEN_LIBRARY_BASE_URL.rstrip('/')}/search.json",
            params={
                "q": query, "page": page, "limit": page_size,
                "fields": "key,title,author_name,cover_i,first_publish_year,subject,ratings_average,edition_count",
            },
            timeout=(3, 10),
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
            raise ValueError("Invalid Open Library search response")
    except (requests.RequestException, ValueError) as error:
        logger.warning("Open Library search unavailable: %s", error)
        if results:
            return {"source": "db", "results": results}
        return {"error": "Book search is temporarily unavailable. Please try again."}

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
        if not work_id.startswith("/works/"):
            work_id = f"/works/{work_id}"
        description = None
        genres = (item.get("subject") or [])[:3]

        # Fetch full descriptions only when a reader opens book details.
        author = (item.get("author_name") or ["Unknown Author"])[0]
        cover_id = item.get("cover_i")
        cover = (
            f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            if cover_id
            else None
        )
        average_rating = item.get("ratings_average")
        book_data = {
            "external_id": work_id,
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

        existing_ids.add(book_obj.id)
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
