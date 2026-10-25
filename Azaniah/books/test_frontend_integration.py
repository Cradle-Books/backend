from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Book, UserBook


class DashboardJWTIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="integration-reader", password="fixture-password")
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        self.reading = Book.objects.create(title="Reading fixture", author="Author", external_id="/works/integration-reading", description="Description", genre=["Fiction"], page_count=320, average_rating=4.2)
        self.recommended = Book.objects.create(title="Recommended fixture", author="Author", external_id="/works/integration-recommended", description="Description", genre=["Fiction"], average_rating=4.0)
        UserBook.objects.create(user=self.user, book=self.reading, status="reading")

    def test_recommendations_accept_existing_jwt_and_exclude_own_shelf(self):
        response = self.client.get("/api/books/recommendations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([book["id"] for book in response.data["results"]], [self.recommended.id])

    def test_recommendations_require_authentication(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/books/recommendations/").status_code, 401)

    def test_library_preserves_page_count_and_status_change_updates_counts(self):
        response = self.client.get("/api/books/library/fetch/")
        entry = response.data["books"][0]
        self.assertEqual(entry["book_details"]["page_count"], 320)
        response = self.client.patch(f'/api/books/library/update/{entry["id"]}/', {"status": "finished"}, format="json")
        self.assertEqual(response.status_code, 200)
        profile = self.client.get("/api/books/profile/").data
        self.assertEqual((profile["reading"], profile["finished"], profile["total_books"]), (0, 1, 1))

    def test_another_readers_entry_cannot_be_changed(self):
        other = User.objects.create_user(username="other-reader", password="fixture-password")
        entry = UserBook.objects.create(user=other, book=self.recommended, status="reading")
        response = self.client.patch(f"/api/books/library/update/{entry.id}/", {"status": "finished"}, format="json")
        self.assertEqual(response.status_code, 404)
        entry.refresh_from_db()
        self.assertEqual(entry.status, "reading")
