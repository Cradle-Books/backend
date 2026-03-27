from django.contrib.auth.hashers import make_password
from django.db import models



class Account(models.Model):
    email = models.EmailField(unique=True)
    First_name = models.CharField(max_length=150, blank=True)
    Last_name = models.CharField(max_length=150, blank=True)
    Password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.Password and not self.Password.startswith('pbkdf2_sha256$'):
            self.Password = make_password(self.Password)
        super().save(*args, **kwargs)

