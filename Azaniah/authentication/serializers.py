from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Account, Profile, Genre

def validate_no_at_symbol(value):
    if '@' in value:
        raise serializers.ValidationError("Username cannot contain '@'.")
    return value

class AccountSerializer(serializers.ModelSerializer):
    Username = serializers.CharField(validators=[validate_no_at_symbol])
    class Meta:
        model = Account
        fields = ['Email', 'Username', 'Password', 'Confirm_Password']
        extra_kwargs = {
            'Password': {'write_only': True},
            'Confirm_Password': {'write_only': True},
        }
#serializer validity for password confirmation is placed here i order to have effect in views.py
    def validate(self, data):
        if data['Password'] != data['Confirm_Password']:
            raise serializers.ValidationError({
                'Confirm_Password': 'Passwords must match.'
            })
        return data

class ProfileSerializer(serializers.ModelSerializer):
    #read only fields gotten from the account
    Email = serializers.EmailField(source='account.Email', read_only=True)
    username = serializers.SerializerMethodField()
    
    # Handle Favourite_genres as a list of genre keys
    Favourite_genres = serializers.SlugRelatedField(
        many=True,
        slug_field='key',
        queryset=Genre.objects.all()
    )

    class Meta:
        model = Profile
        fields = ['Email', 'Username', 'username', 'Phone', 'Country', 'Address', 'Favourite_genres', 'created_at', 'updated_at', 'privacy']

    def get_username(self, profile):
        return profile.Username.strip() or profile.account.Username.strip()


class ChangePasswordSerializer(serializers.Serializer):
    #since no model is associated with this serializer, we use just .Serializer, instead of .ModelSerializer
    old_password = serializers.CharField(write_only = True, required = True)
    new_password = serializers.CharField(write_only = True, required = True, min_length = 8)
    confirm_password = serializers.CharField(write_only = True, required = True, min_length = 8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords must match."})
        return data
    

    