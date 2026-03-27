from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = Account
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'password', 'is_verified', 'provider', 'google_id']
        read_only_fields = ['id', 'is_verified', 'provider', 'google_id']

    def create(self, validated_data):
        raw_password = validated_data.pop('password')
        account = Account(**validated_data)
        account.password = make_password(raw_password)
        account.provider = 'local'
        account.save()
        account.assign_otp()
        return account


class GoogleSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['email', 'first_name', 'last_name', 'google_id']

    def validate(self, attrs):
        if not attrs.get('google_id'):
            raise serializers.ValidationError('google_id is required for Google signup.')
        return attrs

    def create(self, validated_data):
        from django.utils.crypto import get_random_string

        account, created = Account.objects.get_or_create(
            email=validated_data['email'],
            defaults={
                'first_name': validated_data.get('first_name', ''),
                'last_name': validated_data.get('last_name', ''),
                'provider': 'google',
                'is_verified': True,
                'google_id': validated_data['google_id'],
                'password': make_password(get_random_string(20)),
            }
        )
        if not created:
            if account.provider != 'google':
                raise serializers.ValidationError('Email exists with a different signup method.')
            account.google_id = validated_data['google_id']
            account.first_name = validated_data.get('first_name', account.first_name)
            account.last_name = validated_data.get('last_name', account.last_name)
            account.is_verified = True
            account.save()
        account.create_django_user()
        return account
