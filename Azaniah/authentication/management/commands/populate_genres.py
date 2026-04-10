from django.core.management.base import BaseCommand
from Azaniah.authentication.models import Genre, GENRE_CHOICES

class Command(BaseCommand):
    help = 'Populate the database with genre choices'

    def handle(self, *args, **options):
        for key, name in GENRE_CHOICES:
            genre, created = Genre.objects.get_or_create(
                key=key,
                defaults={'name': name}
            )
            if created:
                self.stdout.write(f'Created: {name}')
        
        self.stdout.write(self.style.SUCCESS(f'Total genres: {Genre.objects.count()}'))
