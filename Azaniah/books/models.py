from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

class Book(models.Model):
    title = models.CharField(max_length = 300)
    author = models.CharField(max_length = 150)
    google_books_id = models.CharField(max_length = 250, null = True, blank = True)
    release_date = models.IntegerField(null = True, blank = True)
    genre = models.JSONField(default = list, blank = True)
    cover = models.URLField(blank = True, null = True)
    description = models.CharField(max_length = 250000)
    page_count = models.IntegerField(null = True, blank = True)
    external_id = models.CharField(max_length = 100, unique = True)
    average_rating = models.FloatField(null = True, blank = True)

    def __str__(self):
        return f"{self.title} - {self.author}"


class UserBook(models.Model):

    class Status(models.TextChoices):
        WANT = 'want', 'Want to Read'
        READING = 'reading', 'Reading'
        FINISHED = 'finished', 'Finished'

    user = models.ForeignKey( 
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE
    )#used to link the book to the user and also to know which user has which book in their library. on_delete = models.CASCADE means that if the user is deleted, all their associated UserBook entries will also be deleted. 

    book = models.ForeignKey(
        Book,
        on_delete = models.CASCADE,
        related_name = "user_books"
    )
    #ForeignKey relates objects in a relational database (two models) with a many-to-one relationship
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WANT
    )

    ratings = models.PositiveSmallIntegerField(
        null = True,
        blank = True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.TextField(null = True, blank = True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)
    class Meta:
        #this means that individual fields aren't unique, but only unique as a pair. i.e teni - fences != teni - verity
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"
    
    
    