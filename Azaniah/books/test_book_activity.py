from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from Azaniah.authentication.models import Account, Profile
from .models import Book, UserBook
from .services.book_detail import recent_activity


class BookActivityTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(title="Activity fixture", author="Author", external_id="/works/ACTIVITY", description="Cached description", average_rating=4.2, page_count=320)

    def add_reader(self, handle, privacy="public", status="reading", minutes=0, display=""):
        email = f"{handle}@example.test"
        user = User.objects.create_user(username=email, email=email)
        account = Account.objects.create(Email=email, Username=handle, Password="fixture", Confirm_Password="fixture")
        Profile.objects.create(account=account, Username=display, privacy=privacy)
        UserBook.objects.create(user=user, book=self.book, status=status, status_changed_at=timezone.now() - timedelta(minutes=minutes))
        return user

    def test_book_endpoint_returns_public_and_private_handles_without_emails(self):
        public = self.add_reader("public-reader", display="Public Reader", minutes=2)
        private = self.add_reader("private-reader", privacy="private", status="finished")
        response = self.client.get(f"/api/books/book/{self.book.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page_count"], 320)
        self.assertEqual(response.json()["number_of_readers"], 2)
        self.assertEqual([row["user"] for row in response.json()["recent_activity"]], ["private-reader", "Public Reader"])
        self.assertEqual(response.json()["recent_activity"][0]["user_id"], private.pk)
        self.assertNotIn(public.email, response.content.decode())
        self.assertNotIn(private.email, response.content.decode())

    def test_latest_five_shelf_changes_are_ordered_and_batched(self):
        for index in range(7):
            self.add_reader(f"reader-{index}", minutes=index)
        with self.assertNumQueries(2):
            activity = recent_activity(self.book.pk)
        self.assertEqual(len(activity), 5)
        self.assertEqual([row["user"] for row in activity], [f"reader-{index}" for index in range(5)])

    def test_unresolved_email_usernames_are_never_published(self):
        user = User.objects.create_user(username="orphan@example.test", email="orphan@example.test")
        UserBook.objects.create(user=user, book=self.book, status="want")
        self.assertEqual(recent_activity(self.book.pk), [])

    def test_empty_book_activity_is_an_empty_list(self):
        response = self.client.get(f"/api/books/book/{self.book.pk}/")
        self.assertEqual(response.json()["recent_activity"], [])
        self.assertEqual(response.json()["number_of_readers"], 0)

    def test_initial_shelf_add_uses_creation_time_when_status_time_is_missing(self):
        user = self.add_reader("new-reader", status="want")
        entry = UserBook.objects.get(user=user, book=self.book)
        entry.status_changed_at = None
        entry.save(update_fields=["status_changed_at"])
        activity = recent_activity(self.book.pk)
        self.assertEqual(activity[0]["status_changed_at"], entry.created_at)
