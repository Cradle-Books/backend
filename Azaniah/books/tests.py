from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock, patch

from Azaniah.authentication.models import Account, Profile
from .models import Book, UserBook
from .services.userbook_profile import get_userbook_profile
from .services.search_books import search_books
from .services.book_detail import get_book_detail
from .services.google_books import fetch_google_book


class UserBookProfileTests(TestCase):
    def test_profile_uses_signup_username_from_account_when_profile_is_blank(self):
        email = "reader@example.com"
        user = User.objects.create_user(username=email, email=email, password="test-password")
        account = Account.objects.create(
            Email=email,
            Username="cradle_reader",
            Password="test-password",
            Confirm_Password="test-password",
        )
        Profile.objects.create(account=account)

        profile = get_userbook_profile(user)

        self.assertEqual(profile["username"], "cradle_reader")

    def test_profile_reports_books_in_each_shelf_status(self):
        email = "reader@example.com"
        user = User.objects.create_user(username=email, email=email, password="test-password")
        account = Account.objects.create(
            Email=email,
            Username="cradle_reader",
            Password="test-password",
            Confirm_Password="test-password",
        )
        Profile.objects.create(account=account, Username="cradle_reader")
        for index, status in enumerate(("reading", "want", "finished"), start=1):
            book = Book.objects.create(
                title=f"Book {index}",
                author="Author",
                description="Description",
                external_id=f"/works/OL{index}W",
            )
            UserBook.objects.create(user=user, book=book, status=status)

        profile = get_userbook_profile(user)

        self.assertEqual(profile["total_books"], 3)
        self.assertEqual(profile["reading"], 1)
        self.assertEqual(profile["want_to_read"], 1)
        self.assertEqual(profile["finished"], 1)


class SearchBookCacheTests(TestCase):
    @patch("Azaniah.books.services.search_books.requests.get")
    def test_complete_cached_page_needs_no_external_enrichment(self, mock_get):
        book = Book.objects.create(title="Cached Book", author="Test Author", description="", external_id="/works/CACHED")
        result = search_books("Test Author", page=1, page_size=1)
        self.assertEqual(result["source"], "db")
        self.assertEqual(result["results"][0]["id"], book.id)
        mock_get.assert_not_called()


class GoogleBooksMetadataTests(TestCase):
    @patch("Azaniah.books.services.google_books.requests.get")
    def test_prefers_matching_google_candidate_with_a_rating(self, mock_get):
        response = Mock(status_code=200)
        response.json.return_value = {
            "items": [
                {
                    "id": "unrated",
                    "volumeInfo": {
                        "title": "A Test Book",
                        "authors": ["Test Author"],
                        "description": "First edition",
                    },
                },
                {
                    "id": "rated",
                    "volumeInfo": {
                        "title": "A Test Book",
                        "authors": ["Test Author"],
                        "description": "Rated edition",
                        "averageRating": 4.5,
                    },
                },
            ]
        }
        mock_get.return_value = response

        result = fetch_google_book("A Test Book", "Test Author")

        self.assertEqual(result["google_books_id"], "rated")
        self.assertEqual(result["average_rating"], 4.5)
        self.assertEqual(mock_get.call_args.kwargs["params"]["maxResults"], 20)

    @patch("Azaniah.books.services.google_books.time.sleep")
    @patch("Azaniah.books.services.google_books.requests.get")
    def test_retries_once_when_google_books_returns_503(
        self,
        mock_get,
        mock_sleep,
    ):
        unavailable = Mock(status_code=503)
        success = Mock(status_code=200)
        success.json.return_value = {
            "items": [
                {
                    "id": "rated",
                    "volumeInfo": {
                        "title": "A Test Book",
                        "authors": ["Test Author"],
                        "averageRating": 4.5,
                    },
                }
            ]
        }
        mock_get.side_effect = [unavailable, success]

        result = fetch_google_book("A Test Book", "Test Author")

        self.assertEqual(result["average_rating"], 4.5)
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(1)


class BookDetailMetadataTests(TestCase):
    @patch("Azaniah.books.services.book_detail.fetch_google_book")
    @patch("Azaniah.books.services.book_detail.requests.get")
    def test_enriches_existing_book_with_google_description_and_rating(
        self,
        mock_open_library,
        mock_google_book,
    ):
        book = Book.objects.create(
            title="A Test Book",
            author="Test Author",
            description="",
            external_id="/works/OL123W",
        )
        mock_open_library.return_value = Mock(status_code=404)
        mock_google_book.return_value = {
            "description": "Description from Google Books.",
            "page_count": 240,
            "average_rating": 4.5,
        }

        result, error = get_book_detail(book.id)

        book.refresh_from_db()
        self.assertIsNone(error)
        self.assertEqual(result["description"], "Description from Google Books.")
        self.assertEqual(result["average_rating"], 4.5)
        self.assertEqual(book.description, "Description from Google Books.")
        self.assertEqual(book.average_rating, 4.5)

    @patch("Azaniah.books.services.book_detail.fetch_google_book")
    @patch("Azaniah.books.services.book_detail.requests.get")
    def test_complete_visible_metadata_does_not_fetch_again_without_page_count(
        self,
        mock_open_library,
        mock_google_book,
    ):
        book = Book.objects.create(
            title="A Test Book",
            author="Test Author",
            description="Cached description.",
            average_rating=4.5,
            external_id="/works/OL123W",
        )

        result, error = get_book_detail(book.id)

        self.assertIsNone(error)
        self.assertEqual(result["description"], "Cached description.")
        self.assertEqual(result["average_rating"], 4.5)
        mock_open_library.assert_not_called()
        mock_google_book.assert_not_called()
