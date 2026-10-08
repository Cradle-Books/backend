import requests
from django.conf import settings
import logging
import re
import time
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def _normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _match_score(item, title, author):
    volume = item.get("volumeInfo", {})
    candidate_title = volume.get("title", "")
    candidate_authors = volume.get("authors") or []
    title_score = SequenceMatcher(
        None,
        _normalized(title),
        _normalized(candidate_title),
    ).ratio()
    author_score = max(
        (
            SequenceMatcher(None, _normalized(author), _normalized(candidate))
            .ratio()
            for candidate in candidate_authors
        ),
        default=0,
    )
    has_rating = volume.get("averageRating") is not None
    return title_score, author_score, has_rating


def fetch_google_book(title, author):
    url = "https://www.googleapis.com/books/v1/volumes"

    params = {
        "q": f"intitle:{title}+inauthor:{author}",
        "key": settings.API_KEY,
        "maxResults": 20,
    }

    for attempt in range(2):
        try:
            response = requests.get(url, params=params, timeout=15)
        except requests.RequestException:
            logger.warning(
                "Google Books request failed for %r by %r",
                title,
                author,
                exc_info=True,
            )
            return None

        if response.status_code != 503:
            break
        if attempt == 0:
            time.sleep(1)

    if response.status_code != 200:
        logger.warning(
            "Google Books returned status %s for %r by %r",
            response.status_code,
            title,
            author,
        )
        return None

    items = response.json().get("items", [])

    if not items:
        logger.info("Google Books found no results for %r by %r", title, author)
        return None

    item = max(items, key=lambda candidate: _match_score(candidate, title, author))
    volume = item.get("volumeInfo", {})

    return {
        "google_books_id": item.get("id"),
        "description": volume.get("description"),
        "genre": volume.get("categories", []),
        "cover": (volume.get("imageLinks") or {}).get("thumbnail"),
        "page_count": volume.get("pageCount"),
        "average_rating": volume.get("averageRating"),
    }
