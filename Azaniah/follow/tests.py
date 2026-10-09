from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from Azaniah.authentication.models import Account, Profile
from .models import Following

User = get_user_model()


class FollowApiTests(APITestCase):
    def create_reader(self, username, privacy=Profile.PrivacySettings.PUBLIC):
        email = f"{username}@example.com"
        user = User.objects.create_user(
            username=username,
            email=email,
            password="test-password-123",
        )
        account = Account.objects.create(
            Email=email,
            Username=username,
            Password="test-password-123",
            Confirm_Password="test-password-123",
        )
        Profile.objects.create(
            account=account,
            Username=username,
            privacy=privacy,
        )
        return user

    def test_following_public_profile_creates_accepted_relationship(self):
        reader = self.create_reader("reader")
        self.client.force_authenticate(self.create_reader("follower"))

        response = self.client.post(
            reverse("follow-user"),
            {"following": reader.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["state"], Following.FollowStatus.ACCEPTED)
        self.assertTrue(
            Following.objects.filter(
                follower__username="follower",
                following=reader,
                state=Following.FollowStatus.ACCEPTED,
            ).exists()
        )

    def test_following_private_profile_creates_pending_request(self):
        reader = self.create_reader("private-reader", Profile.PrivacySettings.PRIVATE)
        self.client.force_authenticate(self.create_reader("follower"))

        response = self.client.post(
            reverse("follow-user"),
            {"following": reader.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["state"], Following.FollowStatus.PENDING)

    def test_user_cannot_follow_themselves(self):
        reader = self.create_reader("reader")
        self.client.force_authenticate(reader)

        response = self.client.post(
            reverse("follow-user"),
            {"following": reader.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Following.objects.exists())

    def test_only_recipient_can_accept_pending_follow_request(self):
        requester = self.create_reader("requester")
        recipient = self.create_reader("recipient", Profile.PrivacySettings.PRIVATE)
        stranger = self.create_reader("stranger")
        follow_request = Following.objects.create(
            follower=requester,
            following=recipient,
            state=Following.FollowStatus.PENDING,
        )
        self.client.force_authenticate(stranger)

        response = self.client.post(
            reverse("accept-follow-request", args=[follow_request.pk]),
        )

        self.assertEqual(response.status_code, 404)
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.state, Following.FollowStatus.PENDING)

    def test_recipient_can_accept_pending_follow_request(self):
        requester = self.create_reader("requester")
        recipient = self.create_reader("recipient", Profile.PrivacySettings.PRIVATE)
        follow_request = Following.objects.create(
            follower=requester,
            following=recipient,
            state=Following.FollowStatus.PENDING,
        )
        self.client.force_authenticate(recipient)

        response = self.client.post(
            reverse("accept-follow-request", args=[follow_request.pk]),
        )

        self.assertEqual(response.status_code, 200)
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.state, Following.FollowStatus.ACCEPTED)

    def test_recipient_can_decline_pending_follow_request(self):
        requester = self.create_reader("requester")
        recipient = self.create_reader("recipient", Profile.PrivacySettings.PRIVATE)
        follow_request = Following.objects.create(
            follower=requester,
            following=recipient,
            state=Following.FollowStatus.PENDING,
        )
        self.client.force_authenticate(recipient)

        response = self.client.post(
            reverse("deny-follow-request", args=[follow_request.pk]),
        )

        self.assertEqual(response.status_code, 200)
        follow_request.refresh_from_db()
        self.assertEqual(follow_request.state, Following.FollowStatus.DECLINED)

    def test_pending_request_and_connections_return_expected_shapes(self):
        requester = self.create_reader("requester")
        recipient = self.create_reader("recipient", Profile.PrivacySettings.PRIVATE)
        follow_request = Following.objects.create(
            follower=requester,
            following=recipient,
            state=Following.FollowStatus.PENDING,
        )
        self.client.force_authenticate(recipient)

        pending_response = self.client.get(reverse("pending-follow-requests"))

        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(
            pending_response.data["pending"],
            [{
                "id": follow_request.pk,
                "user_id": requester.pk,
                "username": "requester",
                "state": "pending",
            }],
        )

        follow_request.state = Following.FollowStatus.ACCEPTED
        follow_request.save(update_fields=["state"])
        connections_response = self.client.get(reverse("follow-list"))
        self.assertEqual(connections_response.status_code, 200)
        self.assertEqual(connections_response.data["followers"][0]["username"], "requester")

    def test_authenticated_profile_get_uses_jwt_user_without_get_body(self):
        reader = self.create_reader("reader")
        self.client.force_authenticate(reader)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["username"], "reader")
        self.assertEqual(response.data["profile"]["privacy"], Profile.PrivacySettings.PUBLIC)

    def test_people_search_returns_public_handle_without_email(self):
        reader = self.create_reader("reader")
        self.client.force_authenticate(self.create_reader("follower"))

        response = self.client.get(reverse("people-search"), {"username": "reader"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["username"], "reader")
        self.assertNotIn("email", response.data["results"][0])

    def test_public_profile_endpoint_returns_handle_and_privacy_without_email(self):
        reader = self.create_reader("reader")

        response = self.client.get(
            reverse("public-reader-profile", args=["reader"]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "reader")
        self.assertEqual(response.data["privacy"], Profile.PrivacySettings.PUBLIC)
        self.assertNotIn("email", response.data)
