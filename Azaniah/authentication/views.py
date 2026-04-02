from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import AccountSerializer, ProfileSerializer
from .models import Account, Profile
from rest_framework import status
import logging
import threading
import random
logger = logging.getLogger('Azaniah.authentication')
from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

class AccountView(APIView):
    #these are necessary cause DRF automatically makes them required unless stated otherwise   
    permission_classes = [] 
    authentication_classes = []

    def post(self, request):
        #gathers all data for that serializer
        serializer = AccountSerializer(data = request.data)
        if serializer.is_valid():
            #selects a particular detail from the provided data, name in bracket should match name in serializer
            email = serializer.validated_data['Email'] #using .get() requires curly brackets

            if Account.objects.filter(Email = email).exists() or User.objects.filter(email = email).exists():
                return Response({
                    "error": "Account already exists!",
                    "message": "These details already exist in our system, please sign in!"
                }, status = status.HTTP_400_BAD_REQUEST)


            otp = str(random.randint(100000, 999999))

            cache_data = {
                'user_data': serializer.validated_data,
                'otp': otp
            }
            
            cache.set(f'signup_user_{email}', cache_data, timeout = 600)

            #this defines the email sending function
            def send_email_async():
                """Send email in background thread"""
                import time
                start_time = time.time()
                try:
                    logger.info(f"Starting Signup OTP email send to {email} (background thread)")
                    #importing the function for otp sending
                    from gmail_utils import send_otp_email
                    email_sent = send_otp_email(email, otp)
                    elapsed_time = time.time() - start_time
                    if email_sent:
                        logger.info(f"Signup OTP email sent successfully to {email} (took {elapsed_time:.2f}s)")
                    else:
                        logger.warning(f"Signup OTP email sending failed for {email} (took {elapsed_time:.2f}s)")
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    logger.error(f"Error sending signup OTP email to {email} (took {elapsed_time:.2f}s): {str(e)}", exc_info=True)
            
            #this starts the email sending process
            email_thread = threading.Thread(target=send_email_async, daemon=True)
            email_thread.start()

            return Response({
                "message": "OTP sent successfully, check your email!",
                "Email": "email"
            }, status = status.HTTP_200_OK)
        else:
            return Response(
                serializer.errors, status = status.HTTP_400_BAD_REQUEST)
        
class VerifyOTPView(APIView):
    def post(self, request):
        #requests certain data
        email = request.data.get('Email')
        otp = request.data.get('OTP')

        if not email or not otp:
            return Response({"message": "Email and OTP required"}, status = status.HTTP_400_BAD_REQUEST)
        
        cache_key = f'signup_user_{email}'
        cached_data = cache.get(cache_key)

        if not cached_data:
            return Response({"error": "Signup session expired or invalid email"}, status = status.HTTP_400_BAD_REQUEST)
        
        if cached_data['otp'] != otp:
            return Response({"error": "Invalid OTP"}, status = status.HTTP_400_BAD_REQUEST)
        
        if (Account.objects.filter(Email=email).exists() or
            User.objects.filter(email=email).exists()):
            # Clear cache since registration is not needed
            cache.delete(cache_key)
            return Response({
                "error": "Email already registered",
                "message": "An account with this email already exists. Please sign up instead."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = cached_data['user_data']
        
        #Create Account and Profile
        account = Account(**user_data)
        account.save()  # This will trigger the password hashing in model.save()
        Profile.objects.create(account=account)  # student profile is created alongside user

        # Create Django User for Authentication
        if not User.objects.filter(username=account.Email).exists():
            User.objects.create_user(
                username=account.Email,
                email=account.Email,
                password=user_data.get('Password'),  # Use the raw password from user_data
                first_name=account.First_name,
                last_name=account.Last_name
            )
        
        
        return Response({"message": "Registration successful"}, status=status.HTTP_201_CREATED)

            



