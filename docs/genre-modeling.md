# Genre modeling: JSONField vs ManyToMany

This document explains two approaches for handling favorite genres in the profile model, and when ManyToMany is a stronger design for grouping data.

## Current model (JSONField)

- `Profile.Favourite_genres = models.JSONField(default=list, blank=True)`
- Stores a list of genre keys directly on the profile.
- Example: `["fantasy", "romance", "science_fiction"]`

### Pros
- Quick to implement.
- Simple data shape for small apps.
- No extra table or join required.

### Cons
- Filtering/aggregation is less efficient for large datasets.
- Harder to enforce genre references (no database foreign key integrity).
- Analytical queries (e.g., top genres, users per genre) are more complex.

## Recommended model (ManyToMany) — NOW IMPLEMENTED ✅

### Models

```python
class Genre(models.Model):
    key = models.CharField(max_length=40, unique=True)  # e.g., 'fantasy', 'romance'
    name = models.CharField(max_length=100)  # e.g., 'Fantasy', 'Romance'

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Profile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile')
    Favourite_genres = models.ManyToManyField(Genre, blank=True)
```

### Why this is good
- Explicit junction table handles M2M relations cleanly via Django ORM.
- Query support:
  - `Profile.objects.filter(Favourite_genres__key='fantasy')`
  - `Genre.objects.annotate(user_count=Count('profile')).order_by('-user_count')`
- Enforces genre validity via foreign key references.
- Ideal for grouping and filtering by common categories.

## Use-cases that benefit
1. "Users who like fantasy"
2. "Users who like both fantasy and romance"
3. "Top 10 genres by active accounts"
4. Reporting and recommendation features

## Implementation Status

✅ **Genre and ManyToMany relationship are now fully implemented** in `Azaniah/authentication/models.py`.

### Next steps:
1. Run migrations: `python manage.py makemigrations authentication && python manage.py migrate`
2. Populate genres via Django admin or a fixture using the `GENRE_CHOICES` values.
3. Update serializers to handle M2M relationships (list of genre keys/IDs).

### Migration from past state (if needed)
- If you had JSONField data previously, convert JSON arrays to ManyToMany relations:
  1. Create `Genre` entries for each known genre.
  2. Use data migration to convert JSON array values into ManyToMany links.
  3. Remove old `Favourite_genres` JSONField if migrating fully.

## Conclusion
ManyToMany is especially strong when the app expects:
- frequent genre-based filtering,
- stable genre taxonomy,
- analysis/grouping across users.

For lightweight use with no heavy querying, JSONField remains acceptable.

---

## QuerySet: What it is and how to work with ManyToMany relationships

### What is a QuerySet?

A **QuerySet** is a Django object that represents a database query. It is **not** a Python list — it is a lazy, chainable representation of data that gets executed only when you evaluate it (e.g., iterate, call `.all()`, or slice it).

#### Key differences: QuerySet vs Python list

| Aspect | Python List | QuerySet |
|--------|------------|----------|
| Data structure | In-memory | Lazy database query |
| Methods | `.append()`, `.count()`, `.sort()` | `.filter()`, `.exists()`, `.all()`, `.count()` |
| Iteration | Instant | Evaluated when iterated |
| Memory | Loads all data immediately | Loads only when needed |

### Example
```python
# Python list
genres_list = ['fantasy', 'romance', 'sci-fi']  # In memory right now
if genres_list:  # Checks if list is non-empty
    for item in genres_list:  # Iterates in-memory

# Django QuerySet (from a ManyToMany relationship)
genres_qs = Profile.Favourite_genres.all()  # Not executed yet — lazy query
if genres_qs.exists():  # Executes DB query: COUNT(*) WHERE ...
    for genre in genres_qs:  # Executes DB query to fetch all rows
        print(genre.name)
```

### Working with ManyToMany: `.exists()` and `.all()`

When a model has a ManyToMany field, accessing it returns a **RelatedManager** (not a plain list).

#### `.exists()` — Check if relation exists (efficient)
```python
if self.Favourite_genres.exists():  # Single efficient DB query
    # Genres exist for this profile
```

#### `.all()` — Get all related objects as QuerySet
```python
for genre in self.Favourite_genres.all():  # QuerySet, lazy
    print(genre.name)
```

#### Comparison
```python
# ❌ DO NOT do this with ManyToMany
if self.Favourite_genres:  # Unpredictable; may fail on unsaved objects
    pass

# ✅ DO THIS instead
if self.Favourite_genres.exists():  # Clear, explicit, efficient
    for genre in self.Favourite_genres.all():
        validate_genre(genre)
```

### Why QuerySet matters
- **Efficiency**: Only fetch what you need.
- **Chainability**: `.filter().exclude().order_by()` before executing.
- **Lazy evaluation**: Queries don't run until required.

### In your Profile model
```python
def clean(self):
    if self.pk and self.Favourite_genres.exists():  # ✅ QuerySet check
        for genre in self.Favourite_genres.all():     # ✅ QuerySet iteration
            if genre.key not in valid_choices:
                raise ValidationError(...)
```

This is the correct pattern for ManyToMany relationships.

---

## Serializer patterns for ManyToMany fields

When exposing `Favourite_genres` via API, use a DRF serializer:

```python
from rest_framework import serializers
from .models import Profile, Genre

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'key', 'name']

class ProfileSerializer(serializers.ModelSerializer):
    Favourite_genres = GenreSerializer(many=True, read_only=True)
    Favourite_genres_keys = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        write_only=True,
        source='Favourite_genres'
    )

    class Meta:
        model = Profile
        fields = ['account', 'Username', 'Phone', 'Country', 'Address', 'Favourite_genres', 'Favourite_genres_keys']

    def create(self, validated_data):
        genres = validated_data.pop('Favourite_genres', [])
        profile = Profile.objects.create(**validated_data)
        if genres:
            profile.Favourite_genres.set(genres)
        return profile

    def update(self, instance, validated_data):
        genres = validated_data.pop('Favourite_genres', None)
        if genres is not None:
            instance.Favourite_genres.set(genres)
        return super().update(instance, validated_data)
```

This pattern:
- Returns full genre objects in GET (read_only)
- Accepts genre IDs in POST/PUT (write_only)
- Uses `.set()` for M2M assignment

