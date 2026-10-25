from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    AccountView, 
    VerifyOTPView, 
    LogoutView, 
    LoginView, 
    AccountProfileView,
    ResetPasswordView,
    ResetPasswordConfirmView,
    ChangePasswordView,
    GenreListView,

)

urlpatterns = [
    #Account related endpoints
    path('signup/', AccountView.as_view(), name='signup'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', AccountProfileView.as_view(), name='profile'),
    path('genres/', GenreListView.as_view(), name='profile-genres'),
    
    # Password reset endpoints
    path('password-reset/', ResetPasswordView.as_view(), name='password-reset'),
    path('password-reset/confirm/', ResetPasswordConfirmView.as_view(), name='password-reset-confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

]
