from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Account
from .serializers import AccountSerializer, GoogleSignupSerializer


def _send_email(subject, message, recipient_list):
    sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    send_mail(subject, message, sender, recipient_list, fail_silently=False)


class SignupView(APIView):
    def post(self, request):
        serializer = AccountSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            account.assign_otp()
            _send_email(
                'Your OTP code',
                f'Hi {account.first_name or account.email},\n\nYour OTP code is {account.otp_code}. It expires in 15 minutes.',
                [account.email],
            )
            return Response({'detail': 'Account created. OTP sent to email.'}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({'detail': 'email and otp are required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = get_object_or_404(Account, email=email)
        verified, message = account.verify_otp(otp)

        if not verified:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

        profile_link = getattr(settings, 'PROFILE_URL', 'http://localhost:8000/profile/')
        _send_email(
            'Account verified',
            f'Congratulations {account.first_name or account.email}! Your account is verified.\n\nVisit your profile at {profile_link}',
            [account.email],
        )

        return Response({'detail': 'OTP verified, account activated and Django user created.'}, status=status.HTTP_200_OK)


class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        raw_password = request.data.get('password')

        if not email or not raw_password:
            return Response({'detail': 'email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = get_object_or_404(Account, email=email)

        if not account.is_verified:
            return Response({'detail': 'Account is not verified.'}, status=status.HTTP_403_FORBIDDEN)

        if not check_password(raw_password, account.password):
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({'detail': 'Login successful.', 'user': {
            'email': account.email,
            'first_name': account.first_name,
            'last_name': account.last_name,
        }}, status=status.HTTP_200_OK)


class GoogleSignupView(APIView):
    def post(self, request):
        serializer = GoogleSignupSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            account.create_django_user()

            profile_link = getattr(settings, 'PROFILE_URL', 'http://localhost:8000/profile/')
            _send_email(
                'Welcome to Azaniah',
                f'Hi {account.first_name or account.email},\n\nYour Google sign-up is complete.\n\nComplete your profile here: {profile_link}',
                [account.email],
            )

            return Response({'detail': 'Google signup successful.'}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    def get(self, request):
        email = request.query_params.get('email')
        if not email:
            return Response({'detail': 'email query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = get_object_or_404(Account, email=email)
        return Response({
            'email': account.email,
            'username': account.username,
            'first_name': account.first_name,
            'last_name': account.last_name,
            'is_verified': account.is_verified,
            'provider': account.provider,
        }, status=status.HTTP_200_OK)

    def put(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = get_object_or_404(Account, email=email)
        for field in ['first_name', 'last_name', 'username']:
            if field in request.data:
                setattr(account, field, request.data[field])

        if request.data.get('password'):
            account.set_password(request.data['password'])

        account.save()

        if account.is_verified:
            account.create_django_user()

        return Response({'detail': 'Profile updated.'}, status=status.HTTP_200_OK)

