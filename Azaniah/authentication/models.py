from django.contrib.auth.hashers import make_password
from django.db import models



class Account(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    password = models.CharField(max_length=255)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.Password and not self.Password.startswith('pbkdf2_sha256$'):
            self.Password = make_password(self.Password)
        super().save(*args, **kwargs)

