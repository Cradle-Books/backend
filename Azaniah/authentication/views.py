from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import AccountSerializer, ProfileSerializer, ChangePasswordSerializer
from .models import Account, Profile, Genre
from rest_framework import status
import logging
import threading
import random
import uuid
logger = logging.getLogger('Azaniah.authentication')
from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.hashers import check_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.exceptions import TokenError

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
                'username': request.data.get('Username', ''),
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
    permission_classes = [] 
    authentication_classes = []

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
        Profile.objects.create(
            account=account,
            Username=cached_data.get('username', '')
        )  # student profile is created alongside user

        # Create Django User for Authentication
        if not User.objects.filter(email=account.Email).exists():
            User.objects.create_user(
                username=account.Username,
                email=account.Email,
                password=user_data.get('Password')  # Use the raw password from user_data
            )
        
        
        return Response({"message": "Registration successful"}, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [] 
    authentication_classes = []

    def post(self, request):
        username = request.data.get('Username')
        password = request.data.get('Password')

        if not username or not password:
            return Response({"message": "Username and Password are required"}, status = status.HTTP_400_BAD_REQUEST)
        
        try:
            account = Account.objects.get(Username=username)
        except Account.DoesNotExist:
            return Response(
                {"message": "Invalid Credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not check_password(password, account.Password):
            return Response({"message": "Invalid Credentials"}, status = status.HTTP_400_BAD_REQUEST)
        
        # Django's User username is the Username created during OTP verification.
        user = authenticate(username=account.Username, password=password)

        if user:
            # Generate Tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Login successful',
                'username': user.username,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
class LogoutView(APIView):
    #account needs to be authenticated before it can request logout

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    
    def post(self, request):
        #one would need to login to be able to generate a refresh token
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            # Try to blacklist the token if blacklist app is configured
            try:
                token.blacklist()
            except AttributeError:
                # Blacklist app not configured, but logout is still valid
                # Frontend should discard the token
                pass
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

class GenreListView(APIView):
    """Expose the stored genre keys accepted by ProfileSerializer."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({"genres": list(Genre.objects.order_by("name").values("key", "name"))})


class AccountProfileView(APIView):

    #to access one's profile, authentication is required through provision of a bearer token
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request):
        email = request.user.email
        if not email:
            return Response(
                {"message": "The authenticated user has no email address."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            account = Account.objects.get(Email=email)
            try:
                profile = Profile.objects.get(account=account)
            except Profile.DoesNotExist:
                return Response(
                    {"message": "Profile doesn't exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            serializer = ProfileSerializer(profile)
            
            return Response({
                'message': 'Profile retrieved successfully',
                'profile': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)
        

    def post(self, request): 
        """
        Create or update account profile with additional fields.
        Uses authenticated user's email from JWT token.
        """
        # Get email from authenticated user
        email = request.user.email
        
        if not email:
            return Response({
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get the student registration
            account = Account.objects.get(Email=email)
            
            # Update StudentRegistration fields if provided
            if 'firstname' in request.data:
                account.Firstname = request.data['firstname']
            if 'lastname' in request.data:
                account.Lastname = request.data['lastname']
            account.save()
            
            # Get the profile
            try:
                profile = Profile.objects.get(account = account)
            except Profile.DoesNotExist:
                return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Update the profile with new data
            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                
                # Invalidate cache when profile is updated
                cache_key = f'signup_user_{email}'
                cache.delete(cache_key)
                logger.info(f"Cache invalidated for account profile {email}")
                
                return Response({
                    'message': 'Profile updated successfully',
                    'profile': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Account.DoesNotExist:
            return Response({'error': 'Account not found. Please register first.'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request):
        """
        Partially update student profile fields (PATCH request).
        Allows updating fields like Username, Favourite_genres (list), etc.
        
        Favourite_genres should be a list of genre type values (e.g., ["romance", "horror", "action"])
        
        PRODUCTION MODE (with JWT): Just send the token in headers, no email needed
        TESTING MODE: Include 'email' in request body
        """
        # Try to get email from authenticated user first (production)
        if request.user.is_authenticated:
            email = request.user.email
        else:
            # Fallback to request data for testing
            email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email is required or you must be authenticated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the student registration
            account = Account.objects.get(Email=email)
            
            # Get the profile
            try:
                profile = Profile.objects.get(account=account)
            except Profile.DoesNotExist:
                return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Update the profile with new data (partial update)
            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                
                # Invalidate cache when profile is updated
                cache_key = f'signup_user_{email}'
                cache.delete(cache_key)
                logger.info(f"Cache invalidated for student profile {email}")
                
                return Response({
                    'message': 'Profile updated successfully',
                    'profile': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Account.DoesNotExist:
            return Response({'error': 'Student not found. Please register first.'}, status=status.HTTP_404_NOT_FOUND)

class ResetPasswordView(APIView):
    """
    Initiate password reset process
    Generates reset token, stores it in cache, sends email with link
    Frontend URL in email: http://localhost:3000/reset-password?token=<UUID>
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        email = request.data.get('Email')

        if not email:
            return Response({
                "error": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify account exists
        if not Account.objects.filter(Email=email).exists():
            # Security: Don't reveal if email exists in database
            return Response({
                "message": "If email exists, password reset link will been sent"
            }, status=status.HTTP_200_OK)

        # Generate unique reset token using UUID
        reset_token = str(uuid.uuid4())

        # Store token + email in cache for 10 minutes
        cache_data = {
            'email': email,
            'token': reset_token
        }
        cache.set(f'reset_token_{reset_token}', cache_data, timeout=600)

        # Send email with reset link in background thread
        def send_email_async():
            """Send reset email in background thread"""
            import time
            start_time = time.time()
            try:
                logger.info(f"Starting password reset email send to {email} (background thread)")
                from gmail_utils import send_reset_email
                # Pass frontend_url if you have it in settings, otherwise use default
                email_sent = send_reset_email(email, reset_token)
                elapsed_time = time.time() - start_time
                if email_sent:
                    logger.info(f"Reset password email sent successfully to {email} (took {elapsed_time:.2f}s)")
                else:
                    logger.warning(f"Reset password email sending failed for {email} (took {elapsed_time:.2f}s)")
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Error sending reset password email to {email} (took {elapsed_time:.2f}s): {str(e)}", exc_info=True)

        # Start email thread
        email_thread = threading.Thread(target=send_email_async, daemon=True)
        email_thread.start()

        return Response({
            "message": "Password reset link sent successfully, check your email!",
            "token": reset_token  # Include token in response for testing purposes (remove in production)
        }, status=status.HTTP_200_OK)


class ResetPasswordConfirmView(APIView):
    """
    Confirm password reset with new password
    Frontend sends: token (from URL params) + new_password
    Updates both Account.Password and User.password and clears reset token
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        reset_token = request.data.get('token')
        new_password = request.data.get('new_password')

        # Validate input
        if not reset_token or not new_password:
            return Response({
                "error": "token and new_password are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate password strength
        if len(new_password) < 8:
            return Response({
                "error": "Password must be at least 8 characters long"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify token exists in cache
        cache_key = f'reset_token_{reset_token}'
        cache_data = cache.get(cache_key)

        if not cache_data:
            return Response({
                "error": "Reset link expired or invalid. Please request a new one."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get email from cache
        email = cache_data['email']

        # Find account and update password
        try:
            # Update Account model
            account = Account.objects.get(Email=email)
            account.Password = new_password  # Model.save() will auto-hash
            account.save()

            # Update Django User model to keep in sync
            user = User.objects.get(email=email)
            user.set_password(new_password)  # Django's built-in password hashing
            user.save()

            # Clear the reset token from cache (one-time use)
            cache.delete(cache_key)

            logger.info(f"Password reset successful for {email}")

            return Response({
                "message": "Password reset successfully. You can now login with your new password.",
                "email": email
            }, status=status.HTTP_200_OK)

        except Account.DoesNotExist:
            return Response({
                "error": "Account not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            # If User doesn't exist, still update Account (this shouldn't normally happen)
            logger.warning(f"Django User not found for {email}, but Account exists")
            return Response({
                "error": "User synchronization error. Please contact support."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}", exc_info=True)
            return Response({
                "error": "An error occurred while resetting password"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ChangePasswordView(APIView):
    #authentication is required
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_authenticated or not request.user:
            return Response({
                "error": "Authentication required"
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            email = request.user.email
            
            # Verify old password by authenticating
            user = authenticate(username=email, password=old_password)
            if not user:
                return Response(
                    {"error": "Old password is incorrect."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update password in both Account and User models
            try:
                account = Account.objects.get(Email=email)
                account.Password = new_password
                account.save()  # This triggers hashing in model.save()
                
                # Sync with Django User
                user.set_password(new_password)
                user.save()
                
                return Response(
                    {"message": "Password changed successfully"},
                    status=status.HTTP_200_OK
                )
            except Account.DoesNotExist:
                return Response(
                    {"error": "Account not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                logger.error(f"Error changing password: {str(e)}", exc_info=True)
                return Response(
                    {"error": "An error occurred while changing password"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        
        





            
        
