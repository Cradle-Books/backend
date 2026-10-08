from django.contrib.auth.hashers import make_password
from django.db import models

# Genre model for storing available book genres
class Genre(models.Model):
    key = models.CharField(max_length=40, unique=True)  # e.g., 'fantasy', 'romance'
    name = models.CharField(max_length=100)  # e.g., 'Fantasy', 'Romance'
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

GENRE_CHOICES = [
    ('action', 'Action'),
    ('biography', 'Biography'),
    ('children', 'Children'),
    ('contemporary_fiction', 'Contemporary Fiction'),
    ('dystopian', 'Dystopian'),
    ('fantasy', 'Fantasy'),
    ('graphic_novel', 'Graphic Novel'),
    ('historical_fiction', 'Historical Fiction'),
    ('horror', 'Horror'),
    ('literary_fiction', 'Literary Fiction'),
    ('mystery', 'Mystery'),
    ('others', 'Others'),
    ('religion_&_spirituality', 'Religion & Spirituality'),
    ('romance', 'Romance'),
    ('science_fiction', 'Science Fiction'),
    ('thriller_&_suspense', 'Thriller & Suspense'),
    ('travel', 'Travel'),
    ('true_crime', 'True Crime'),
    ('young_adult', 'Young Adult'),
]

class Account(models.Model):
    Email = models.EmailField(unique=True)
    Username = models.CharField(max_length=150, unique=True)
    Password = models.CharField(max_length=255)
    Confirm_Password = models.CharField(max_length=255)


    def save(self, *args, **kwargs):
        if self.Password and not self.Password.startswith('pbkdf2_sha256$'):
            self.Password = make_password(self.Password)
        if self.Confirm_Password and not self.Confirm_Password.startswith('pbkdf2_sha256$'):
            self.Confirm_Password = make_password(self.Confirm_Password)
        super().save(*args, **kwargs)

class Profile(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE, 
        related_name='profile')
    
    #these fields are optional and can be filled at any time
    Username = models.CharField(max_length=150, blank=True)
    Phone = models.CharField(max_length=20, blank=True)
    Country = models.CharField(max_length=100, blank=True)
    Address = models.CharField(max_length=255, blank=True)
    #ManyToMany field to store user's favourite genres, allowing multiple selections,
    #will be very useful for our recommendation system and finding friends with similar tastes
    Favourite_genres = models.ManyToManyField(Genre, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Validate Favourite_genres contains only valid choices"""
        from django.core.exceptions import ValidationError

        valid_choices = [choice[0] for choice in GENRE_CHOICES]

        # For a ManyToManyField, use .exists() and .all() instead of treating as a plain python list - it's a  queryset/related manager
        if self.pk and self.Favourite_genres.exists():
            for genre in self.Favourite_genres.all():
                if genre.key not in valid_choices:
                    raise ValidationError({
                        'Favourite_genres': f'Invalid favourite genre: {genre.key}. Must be one of {valid_choices}'
                    })

        # New objects may not have M2M relation assigned until after save and m2m operations.
        # If you're working with a serializer or form, validate input values there directly.

    
    def save(self, *args, **kwargs):
        """Override save to call clean()"""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Profile for {self.account.Email}"

    # Property methods to easily access Account fields
    @property
    def firstname(self):
        """Access firstname from Account"""
        return self.account.First_name
    
    @property
    def lastname(self):
        """Access lastname from Account"""
        return self.account.Last_name
    
    @property
    def email(self):
        """Access email from Account"""
        return self.account.Email
    
