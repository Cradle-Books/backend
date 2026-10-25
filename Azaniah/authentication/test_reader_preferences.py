from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Account, Profile, Genre
from Azaniah.follow.models import Following
from Azaniah.books.models import Book, UserBook


class ReaderPreferencesTests(APITestCase):
    def setUp(self):
        self.password = "reader-password-123"
        self.user = self.reader("reader")
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def reader(self, name):
        email = f"{name}@example.test"
        user = User.objects.create_user(username=email, email=email, password=self.password)
        account = Account.objects.create(Email=email, Username=name, Password=self.password, Confirm_Password=self.password)
        Profile.objects.create(account=account, Username=name)
        return user

    def test_private_preference_persists_and_requires_follow_approval(self):
        response = self.client.patch(reverse("profile"), {"privacy": "private"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("profile")).data["profile"]["privacy"], "private")
        other = self.reader("follower")
        self.client.force_authenticate(other)
        response = self.client.post(reverse("follow-user"), {"following": self.user.pk}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["state"], Following.FollowStatus.PENDING)

    def test_public_preference_accepts_new_follow_immediately(self):
        self.client.patch(reverse("profile"), {"privacy": "public"}, format="json")
        self.client.force_authenticate(self.reader("follower"))
        response = self.client.post(reverse("follow-user"), {"following": self.user.pk}, format="json")
        self.assertEqual(response.data["data"]["state"], Following.FollowStatus.ACCEPTED)

    def test_profile_edits_and_genre_keys_round_trip(self):
        Genre.objects.create(key="fantasy", name="Fantasy")
        response = self.client.patch(reverse("profile"), {"Username": "Reader Name", "Country": "Nigeria", "Phone": "+234123", "Favourite_genres": ["fantasy"]}, format="json")
        self.assertEqual(response.status_code, 200)
        profile = self.client.get(reverse("profile")).data["profile"]
        self.assertEqual(profile["username"], "Reader Name")
        self.assertEqual(profile["Favourite_genres"], ["fantasy"])
        self.assertEqual(profile["Country"], "Nigeria")

    def test_genres_are_public_and_only_include_stored_keys(self):
        Genre.objects.create(key="fantasy", name="Fantasy")
        self.client.credentials()
        response = self.client.get(reverse("profile-genres"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"genres": [{"key": "fantasy", "name": "Fantasy"}]})

    def test_invalid_privacy_is_rejected_and_own_profile_requires_auth(self):
        response = self.client.patch(reverse("profile"), {"privacy": "everyone"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.client.credentials()
        self.assertEqual(self.client.get(reverse("profile")).status_code, 401)

    def test_missing_profile_returns_404(self):
        Profile.objects.filter(account__Email=self.user.email).delete()
        self.assertEqual(self.client.get(reverse("profile")).status_code, 404)

    def test_shelf_rating_status_and_remove_use_entry_id(self):
        book = Book.objects.create(title="Book", author="Author", external_id="/works/PREF", description="")
        entry = UserBook.objects.create(book=book, user=self.user, status="want")
        response = self.client.patch(f"/api/books/library/update/{entry.pk}/", {"ratings": 5, "status": "finished"}, format="json")
        self.assertEqual(response.status_code, 200)
        row = self.client.get("/api/books/library/fetch/").data["books"][0]
        self.assertEqual((row["ratings"], row["status"]), (5, "finished"))
        self.assertEqual(self.client.delete(f"/api/books/library/delete/{entry.pk}/").status_code, 204)
        self.assertFalse(UserBook.objects.filter(pk=entry.pk).exists())

    def test_password_change_updates_login_credentials(self):
        response = self.client.post(reverse("change-password"), {"old_password": self.password, "new_password": "changed-password-123", "confirm_password": "changed-password-123"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("changed-password-123"))
