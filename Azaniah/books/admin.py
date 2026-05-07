from django.contrib import admin
from .models import Book, UserBook

# Register your models here.
admin.site.register(Book)
admin.site.register(UserBook)
