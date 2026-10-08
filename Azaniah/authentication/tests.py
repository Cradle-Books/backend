from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class VerifyOTPViewTests(TestCase):
    def setUp(self):
        self.email = "reader@example.com"
        self.password = "test-password-123"
        cache.set(
            f"signup_user_{self.email}",
            {
                "user_data": {
                    "Email": self.email,
                    "Username": "reader",
                    "Password": self.password,
                    "Confirm_Password": self.password,
                },
                "username": "reader",
                "otp": "123456",
            },
            timeout=600,
        )

    def tearDown(self):
        cache.delete(f"signup_user_{self.email}")

    def test_verification_creates_account_profile_and_django_user(self):
        response = self.client.post(
            reverse("verify-otp"),
            {"Email": self.email, "OTP": "123456"},
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email=self.email)
        self.assertEqual(user.username, self.email)
        self.assertEqual(user.first_name, "")
        self.assertTrue(user.check_password(self.password))

    def test_login_accepts_account_username_and_returns_tokens(self):
        User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
        )
        from .models import Account

        Account.objects.create(
            Email=self.email,
            Username="reader",
            Password=self.password,
            Confirm_Password=self.password,
        )

        response = self.client.post(
            reverse("login"),
            {"Username": "reader", "Password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], self.email)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
