from rest_framework.response import Response
from ..models import UserBook
from django.db.models import Avg

def get_userbook_profile(user):
        
    user_book = UserBook.objects.filter(user=user)

    total_books = user_book.count()
    reading_qs = user_book.filter(status="reading")
    finished = user_book.filter(status="finished").count()
    want_to_read = user_book.filter(status="want").count()

    average_rating = user_book.filter(
        ratings__isnull=False
    ).aggregate(avg=Avg("ratings"))["avg"]

    # 🔥 CURRENTLY READING PREVIEW (LIMITED)
    reading_preview = reading_qs.select_related("book")[:5]

    currently_reading_preview = [
        {
            "id": ub.book.id,
            "title": ub.book.title,
            "author": ub.book.author,
            "cover": ub.book.cover
        }
        for ub in reading_preview
    ]

    return {
        "username": user.username,
        "total_books": total_books,
        "reading": reading_qs.count(),
        "finished": finished,
        "want_to_read": want_to_read,
        "average_rating": round(average_rating, 2) if average_rating else None,
        "currently_reading_preview": currently_reading_preview
    }