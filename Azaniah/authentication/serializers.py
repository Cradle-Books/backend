from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Account, Profile


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['Email', 'First_name', 'Last_name', 'Password']

class ProfileSerializer(serializers.ModelSerializer):
    #read only fields gotten from the account
    First_name = serializers.CharField(read_only=True)
    Last_name = serializers.CharField(read_only=True)
    Email = serializers.EmailField(read_only=True)

    class Meta:
        model = Profile
        fields = ['Email', 'First_name','Last_name', 'Username', 'Phone', 'Country', 'Address', 'Favourite_genres', 'created_at', 'update_at']


