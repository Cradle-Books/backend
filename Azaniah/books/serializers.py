from rest_framework import serializers
from .models import Book, UserBook

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author', 'genre', 'cover', 'description', 'release_date', 'page_count', 'external_id', 'google_books_id']

class UserBookSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserBook
        fields = ['id', 'book', 'status', 'ratings', 'review', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_book(self, value):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context missing")
        
        user = request.user
        if UserBook.objects.filter(user=user, book=value).exists():
            raise serializers.ValidationError(
                "Book already exists in your library."
            )
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context missing")
        
        user = request.user
        user_book = UserBook.objects.create(
            user=user,
            **validated_data
        )
        return user_book