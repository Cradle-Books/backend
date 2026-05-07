from django.db import models
from django.conf import settings

# Create your models here.

class Book(models.Model):
    title = models.CharField(max_length = 300)
    author = models.CharField(max_length = 150)
    release_date = models.IntegerField(null = True, blank = True)
    genre = models.JSONField(default = list, blank = True)
    cover = models.URLField(blank = True)
    description = models.CharField(max_length = 15000)
    external_id = models.CharField(max_length = 100, unique = True)

    def __str__(self):
        return self.title


class UserBook(models.Model):

    class Status(models.TextChoices):
        NONE = 'none', 'None'
        WANT = 'want', 'Want to Read'
        READING = 'reading', 'Reading'
        FINISHED = 'finished', 'Finished'

    user = models.ForeignKey( 
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE
    ) 
    book = models.ForeignKey(
        Book,
        on_delete = models.CASCADE,
        related_name = "book_info"
    )
    #ForeignKey relates objects in a relational database (two models) with a many-to-one relationship
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NONE
    )

    ratings = models.PositiveSmallIntegerField(null = True, blank = True)
    review = models.TextField(null = True, blank = True)
    class Meta:
        #this means that individual fields aren't unique, but only unique as a pair. i.e teni - fences != teni - verity
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"
    
    
    