import requests
from ..models import Book
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

def fetch_google_book(title, author):
    url = "https://www.googleapis.com/books/v1/volumes"

    params = {
        "q": f"intitle:{title}+inauthor:{author}",
        "key": settings.API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    items = response.json().get("items", [])

    if not items:
        return None

    item = items[0]
    volume = item.get("volumeInfo", {})

    return {
        "google_books_id": item.get("id"),
        "description": volume.get("description"),
        "genre": volume.get("categories", []),
        "cover": volume.get("imageLinks", {}).get("thumbnail"),
        "page_count": volume.get("pageCount")
    }
