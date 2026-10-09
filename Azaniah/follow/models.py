from django.db import models
from django.conf import settings
from django.db.models import Q, F


# Create your models here.
class Following(models.Model):
    class FollowStatus(models.TextChoices):
        ACCEPTED = "ACP", "accepted"
        PENDING = "PND", "pending"
        DECLINED = "DCD", "declined"

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_set'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers_set'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(
        max_length = 10,
        choices = FollowStatus.choices
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_followers"),
            models.CheckConstraint(condition=~Q(follower=F("following")), name="prevent_self_follow"),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"
