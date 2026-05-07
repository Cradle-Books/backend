from rest_framework import serializers
from .models import Book, UserBook

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author', 'genre', 'image', 'description']

class UserBookSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserBook
        fields = ['user', 'book', 'status', 'ratings', 'review']