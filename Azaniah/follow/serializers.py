from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Following

User = get_user_model()


class FollowCreateSerializer(serializers.Serializer):
    following = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())


class FollowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Following
        fields = ["id", "follower", "following", "created_at", "state"]
        read_only_fields = fields
