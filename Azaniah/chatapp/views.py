from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

# Create your views here.
class CurrentChatUserView(APIView):
    authentication_classes = [JWTAuthentication] #validates the access token of the user and identifies them
    permission_classes = [IsAuthenticated] #only an authenticated user can be granted access(prevents unauthenticated requests)

    def get(self, request):
        return Response({
            "id": request.user.id, #request.user holds the user identified by the validated token
            "username": request.user.username,
        })

