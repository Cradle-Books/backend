from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Account, Profile, Genre


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['Email', 'First_name', 'Last_name', 'Password']

class ProfileSerializer(serializers.ModelSerializer):
    #read only fields gotten from the account
    First_name = serializers.CharField(source='account.First_name', read_only=True)
    Last_name = serializers.CharField(source='account.Last_name', read_only=True)
    Email = serializers.EmailField(source='account.Email', read_only=True)
    
    # Handle Favourite_genres as a list of genre keys
    Favourite_genres = serializers.SlugRelatedField(
        many=True,
        slug_field='key',
        queryset=Genre.objects.all()
    )

    class Meta:
        model = Profile
        fields = ['Email', 'First_name','Last_name', 'Username', 'Phone', 'Country', 'Address', 'Favourite_genres', 'created_at', 'updated_at']


class ChangePasswordSerializer(serializers.Serializer):
    #since no model is associated with this serializer, we use just .Serializer, instead of .ModelSerializer
    old_password = serializers.CharField(write_only = True, required = True)
    new_password = serializers.CharField(write_only = True, required = True, min_length = 8)
    confirm_password = serializers.CharField(write_only = True, required = True, min_length = 8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords must match."})
        return data
    
    