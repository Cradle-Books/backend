from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from Azaniah.authentication.models import Account, Profile
from .models import Following


class CommunityConnectionTests(APITestCase):
    def reader(self, name):
        email = f"{name}@example.test"
        user = User.objects.create_user(username=email, email=email)
        account = Account.objects.create(Email=email, Username=name, Password="fixture", Confirm_Password="fixture")
        Profile.objects.create(account=account)
        return user

    def setUp(self):
        self.me = self.reader("me")
        self.other = self.reader("other")
        self.client.force_authenticate(self.me)

    def test_outgoing_requests_are_separate_from_accepted_connections(self):
        request = Following.objects.create(follower=self.me, following=self.other, state=Following.FollowStatus.PENDING)
        response = self.client.get(reverse("follow-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["following"], [])
        self.assertEqual(response.data["outgoing_pending"], [{"id": request.pk, "user_id": self.other.pk, "username": "other", "state": "pending"}])
        self.assertNotIn(self.other.email, response.content.decode())

    def test_cancel_own_pending_request_by_relationship_id(self):
        request = Following.objects.create(follower=self.me, following=self.other, state=Following.FollowStatus.PENDING)
        response = self.client.delete(reverse("unfollow-user", args=[request.pk]))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(reverse("follow-list")).data["outgoing_pending"], [])

    def test_cannot_cancel_an_incoming_relationship(self):
        request = Following.objects.create(follower=self.other, following=self.me, state=Following.FollowStatus.PENDING)
        response = self.client.delete(reverse("unfollow-user", args=[request.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Following.objects.filter(pk=request.pk).exists())

    def test_declined_relationship_is_not_listed_as_outgoing(self):
        Following.objects.create(follower=self.me, following=self.other, state=Following.FollowStatus.DECLINED)
        self.assertEqual(self.client.get(reverse("follow-list")).data["outgoing_pending"], [])
