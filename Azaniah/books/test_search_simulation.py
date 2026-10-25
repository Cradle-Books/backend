import os
import time
from unittest import skipUnless
from django.test import TestCase, override_settings
from .models import Book


@skipUnless(os.getenv("SEARCH_SIMULATION_URL"), "Start the search simulation and set SEARCH_SIMULATION_URL")
@override_settings(OPEN_LIBRARY_BASE_URL=os.getenv("SEARCH_SIMULATION_URL", ""))
class SearchSimulationTests(TestCase):
    def search(self, query, page=1):
        return self.client.get("/api/books/search/", {"q": query, "page": page, "page_size": 12})

    def test_search_returns_twelve_books_and_preserves_ratings(self):
        response = self.search("healthy")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 12)
        self.assertEqual(response.data["results"][0]["average_rating"], 4.2)
        # Metadata not present in search is fetched later via book detail.
        self.assertEqual(response.data["results"][0]["description"], "")
        self.assertEqual(Book.objects.count(), 12)

    def test_page_two_returns_next_external_page(self):
        response = self.search("healthy", page=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["work_id"], "/works/SIM12W")

    def test_upstream_error_preserves_partial_cached_results(self):
        book = Book.objects.create(title="unavailable book", author="Author", external_id="/works/CACHE", description="Cached description")
        response = self.search("unavailable")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source"], "db")
        self.assertEqual(response.data["results"][0]["id"], book.id)

    def test_invalid_json_returns_service_unavailable(self):
        self.assertEqual(self.search("malformed").status_code, 503)

    def test_slow_upstream_returns_error_before_frontend_timeout(self):
        started = time.monotonic()
        response = self.search("slow")
        elapsed = time.monotonic() - started
        self.assertEqual(response.status_code, 503)
        self.assertIn("temporarily unavailable", response.data["message"])
        self.assertGreaterEqual(elapsed, 9)
        self.assertLess(elapsed, 18)
