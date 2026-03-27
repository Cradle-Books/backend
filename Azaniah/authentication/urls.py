from django.urls import path
from .views import SignupView, VerifyOTPView, LoginView, GoogleSignupView, ProfileView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('google-signup/', GoogleSignupView.as_view(), name='google-signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
