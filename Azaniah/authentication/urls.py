from django.urls import path
from .views import AccountView, VerifyOTPView

urlpatterns = [
    path('signup/', AccountView.as_view(), name='signup'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
]
