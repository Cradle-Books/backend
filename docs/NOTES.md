# Technical Notes & Best Practices

## Table of Contents
1. [Genre modeling: JSONField vs ManyToMany](#genre-modeling)
2. [SlugRelatedField in Serializers](#slugrelatedfield)
3. [Source Parameter](#source-parameter)
4. [Populating Data via Migrations](#populate-genres)
5. [Common Serializer Patterns](#serializer-patterns)
6. [UUID Tokens & Security](#uuid-tokens)
7. [Password Reset Flow](#password-reset-flow)
8. [Gmail API Token Refresh](#gmail-api-token)
9. [Dual Password Hashing](#dual-password-hashing)
10. [DRF APIView: Class-Level vs Method-Level Configuration](#drf-auth-config)

---

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

## SlugRelatedField {#slugrelatedfield}

### What is it?

`SlugRelatedField` is a DRF serializer field that represents a related object **by a single field value** (the "slug") instead of by its primary key (ID). It's perfect for working with related objects using a human-readable identifier.

### When to use

- You have a unique identifier on the related model (like `key` or `username`)
- You want API consumers to work with **string identifiers** instead of numeric IDs
- Example: Send `["romance", "action"]` instead of `[1, 3]` for genres

### Example in ProfileSerializer

```python
from rest_framework import serializers

class ProfileSerializer(serializers.ModelSerializer):
    # This field represents Genre objects by their 'key'
    Favourite_genres = serializers.SlugRelatedField(
        many=True,                          # Handle ManyToMany relationship
        slug_field='key',                   # Use Genre.key as the identifier
        queryset=Genre.objects.all()        # Allowed values for writing
    )

    class Meta:
        model = Profile
        fields = [..., 'Favourite_genres']
```

### How it works

**Reading (Serialization):**
```json
// When fetching a profile, genres appear as keys:
{
  "Favourite_genres": ["romance", "fantasy", "sci-fi"]
}
```

**Writing (Deserialization):**
```json
// When PATCHing a profile, send keys:
{
  "Favourite_genres": ["action", "horror", "thriller_&_suspense"]
}
```

The serializer automatically:
- Looks up `Genre` objects matching those keys
- Links them to the profile's ManyToMany field
- Returns an error if a key doesn't exist (e.g., `"Object with key=invalid_genre does not exist."`)

### Parameters Explained

| Parameter | Purpose |
|-----------|---------|
| `many=True` | Indicates this is a ManyToMany/related manager (list of items) |
| `slug_field='key'` | The field on Genre model to use as identifier |
| `queryset=Genre.objects.all()` | All available genres that can be assigned (required for write operations) |
| `read_only=True` | (optional) If set, can't be written to, only read from |

### Common Pitfalls

**❌ Forgetting queryse:**
```python
Favourite_genres = serializers.SlugRelatedField(
    many=True,
    slug_field='key'
    # Missing queryset - PATCH/POST will fail!
)
```

**❌ Using slug_field for a field that's not unique:**
```python
# If Genre.name isn't unique, lookups will fail arbitrarily
Favourite_genres = serializers.SlugRelatedField(
    many=True,
    slug_field='name'  # Bad if multiple genres have same name
)
```

**✅ Correct template:**
```python
Favourite_genres = serializers.SlugRelatedField(
    many=True,
    slug_field='key',  # Use a unique field
    queryset=Genre.objects.all()
)
```

---

## Source Parameter {#source-parameter}

### What is it?

The `source` parameter tells a serializer field **where to find the value** on the model. It's especially useful for:
- Fields from **related objects** (ForeignKey, OneToOne, etc.)
- **Properties** and **methods** on the model
- **Nested field access** across relationships

### Example in ProfileSerializer

```python
class ProfileSerializer(serializers.ModelSerializer):
    # Profile model doesn't have these fields directly
    # They're on the related Account model via OneToOneField
    First_name = serializers.CharField(source='account.First_name', read_only=True)
    Last_name = serializers.CharField(source='account.Last_name', read_only=True)
    Email = serializers.EmailField(source='account.Email', read_only=True)

    class Meta:
        model = Profile
        fields = ['Email', 'First_name', 'Last_name', ...]
```

### How it works

Without `source`:
```python
First_name = serializers.CharField()  
# Looks for Profile.First_name → doesn't exist → error or missing field
```

With `source`:
```python
First_name = serializers.CharField(source='account.First_name', read_only=True)
# Traverses: Profile.account (OneToOne) → Account.First_name → gets value
```

### Common Usage Patterns

**1. Related Object Fields (Most Common)**
```python
# Profile has OneToOneField to Account
Email = serializers.EmailField(source='account.Email', read_only=True)
# Reads from: profile_instance.account.Email
```

**2. Model Methods/Properties**
```python
class Profile(models.Model):
    @property
    def full_name(self):
        return f"{self.account.First_name} {self.account.Last_name}"

# In serializer:
full_name = serializers.SerializerMethodField(source='full_name')
```

**3. Renaming Fields**
```python
# API shows 'genre_list' but model field is 'Favourite_genres'
genre_list = serializers.SlugRelatedField(
    source='Favourite_genres',
    many=True,
    slug_field='key',
    queryset=Genre.objects.all()
)
```

**4. Nested Relationships (Advanced)**
```python
# Account > Profile > Favourite_genres > Genre
genre_keys = serializers.CharField(source='profile.Favourite_genres.all', many=True)
```

### read_only vs Writable source

**❌ Writable with source (risky):**
```python
Email = serializers.EmailField(source='account.Email')
# PATCH sends: {"Email": "new@example.com"} →modifies Account.Email
# Can cause unintended side effects and data corruption
```

**✅ Read-only with source (safe):**
```python
Email = serializers.EmailField(source='account.Email', read_only=True)
# Can't be modified via API, only displayed
# Safe and predictable
```

---

## Populating Data via Migrations {#populate-genres}

### The Problem

Migrations create **schema only** (tables, columns), not **data**.

```bash
python manage.py migrate
# ✅ Genre table created, empty
# ❌ No genres actually in the database
```

### Solution 1: Management Command (Quick)

Created: `Azaniah/authentication/management/commands/populate_genres.py`

```python
python manage.py populate_genres
```

Pros: Simple, reusable, can run anytime
Cons: Manual step, teammates might forget

### Solution 2: Data Migration (Best)

Automatically runs during `python manage.py migrate`:

```bash
python manage.py makemigrations authentication --empty --name populate_genres
```

Edit the generated file in `migrations/000X_populate_genres.py`:

```python
from django.db import migrations
from Azaniah.authentication.models import GENRE_CHOICES

def populate_genres(apps, schema_editor):
    Genre = apps.get_model('authentication', 'Genre')
    for key, name in GENRE_CHOICES:
        Genre.objects.get_or_create(key=key, defaults={'name': name})

def reverse_genres(apps, schema_editor):
    Genre = apps.get_model('authentication', 'Genre')
    Genre.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0002_genre_rename_email_account_email_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_genres, reverse_genres),
    ]
```

Then run:
```bash
python manage.py migrate
# ✅ Genres created automatically
```

Pros: Automatic, ensures consistency, reversible, documented
Cons: Extra migration file

### Key Differences

| Aspect | Management Command | Data Migration |
|--------|-------------------|-----------------|
| Automatic | ❌ Manual step | ✅ Auto with migrate |
| Reversible | ❌ Not reversible | ✅ Can undo |
| Consistency | ⚠️ Depends on teams | ✅ Guaranteed |
| Teammates | ❌ Must know to run | ✅ "Just migrate" |

**Recommendation**: Use data migrations for required seed data, management commands for optional operations.

---

## Common Serializer Patterns {#serializer-patterns}

### Pattern 1: Read-Only Source Fields

```python
class ProfileSerializer(serializers.ModelSerializer):
    # Show related object data without allowing writes
    First_name = serializers.CharField(source='account.First_name', read_only=True)
    Last_name = serializers.CharField(source='account.Last_name', read_only=True)
    Email = serializers.EmailField(source='account.Email', read_only=True)
```

**Use when**: Need to display related data but it's managed elsewhere

### Pattern 2: SlugRelatedField for ManyToMany

```python
class ProfileSerializer(serializers.ModelSerializer):
    Favourite_genres = serializers.SlugRelatedField(
        many=True,
        slug_field='key',
        queryset=Genre.objects.all()
    )
```

**Use when**: Users work with human-readable identifiers not IDs

### Pattern 3: Partial Updates

```python
# In view:
serializer = ProfileSerializer(profile, data=request.data, partial=True)
```

**Use when**: PATCH endpoint should allow any field subset

### Pattern 4: SerializerMethodField

```python
class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.account.First_name} {obj.account.Last_name}"
```

**Use when**: Computed fields, read-only derived data

### Pattern 5: Custom Field Validation

```python
class ProfileSerializer(serializers.ModelSerializer):
    def validate_Phone(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Phone must contain only digits")
        return value
```

**Use when**: Field-level business logic validation

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

## Book Model and UserBook Relationships

### Book Model

The `Book` model represents a book in the catalog.

```python
class Book(models.Model):
    title = models.CharField(max_length=300)
    author = models.CharField(max_length=150)
    release_date = models.IntegerField(null=True, blank=True)  # Year only
    genre = models.JSONField(default=list, blank=True)  # List of genre tags
    cover = models.URLField(blank=True)  # Book cover image URL
    description = models.CharField(max_length=15000)
    external_id = models.CharField(max_length=100, unique=True)  # Open Library ID or custom

    def __str__(self):
        return self.title
```

**Key Design Decisions**:
- **JSONField for genre**: Flexible list of strings (e.g., `["fantasy", "adventure"]`) from external sources
- **external_id (unique)**: Prevents duplicate books from Open Library or other APIs
- **Nullable release_date**: Not all books have clear publication dates
- **description (CharField, not TextField)**: Fixed max length for consistency
- **cover (URLField)**: Stores external image URLs, not file uploads

**Use Cases**:
- Search results from both local DB and Open Library API
- Book recommendations based on user preferences
- Tracking user's reading list and ratings

### UserBook Model

The `UserBook` model is a through table that tracks a user's relationship with books.

```python
class UserBook(models.Model):
    class Status(models.TextChoices):
        NONE = 'none', 'None'
        WANT = 'want', 'Want to Read'
        READING = 'reading', 'Reading'
        FINISHED = 'finished', 'Finished'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='book_info'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NONE
    )
    ratings = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5 or custom
    review = models.TextField(null=True, blank=True)  # User's written review

    class Meta:
        unique_together = ('user', 'book')  # User can't add same book twice

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"
```

**Key Design Decisions**:
- **ForeignKey to AUTH_USER_MODEL**: Links to Django's User model via settings reference (flexible)
- **ForeignKey to Book with CASCADE**: Delete book → delete all related UserBook entries
- **unique_together constraint**: Each user can only have ONE entry per book (prevents duplicates)
- **Status field**: TextChoices with readable display names
- **Nullable ratings/review**: User can track status without leaving a review yet

**Relationship**: Many-to-Many between User and Book, but with extra data (status, ratings, review)

**Use Cases**:
- "Mark as want to read" / "Mark as reading" / "Mark as finished"
- Store user ratings (1-5 stars)
- Store user reviews and comments
- Track reading history and statistics
- Recommend books based on user's reading habits

### How UserBook Works

**Scenario 1: User finds book and adds to reading list**
```python
user = User.objects.get(username='john')
book = Book.objects.get(external_id='open_library_123')

# Create a tracking entry
user_book = UserBook.objects.create(
    user=user,
    book=book,
    status=UserBook.Status.WANT  # "Want to Read"
)
```

**Scenario 2: User updates status after reading**
```python
user_book = UserBook.objects.get(user=user, book=book)
user_book.status = UserBook.Status.FINISHED
user_book.ratings = 5  # 5-star rating
user_book.review = "Amazing book! Loved every page."
user_book.save()
```

**Scenario 3: Query user's reading list**
```python
# Get all books user has read
finished_books = UserBook.objects.filter(
    user=user,
    status=UserBook.Status.FINISHED
).select_related('book')

for entry in finished_books:
    print(f"{entry.book.title}: {entry.ratings}/5 stars")
```

**Scenario 4: Prevent duplicate entries**
```python
# This will throw IntegrityError (unique_together violation)
UserBook.objects.create(
    user=user,
    book=book,  # Same user-book pair already exists
    status=UserBook.Status.WANT
)  # ❌ FAILS - unique_together prevents this

# Instead, update existing entry
user_book, created = UserBook.objects.get_or_create(
    user=user,
    book=book,
    defaults={'status': UserBook.Status.WANT}
)
if not created:  # Already existed
    user_book.status = UserBook.Status.READING
    user_book.save()
```

---

## Hybrid Book Search Strategy

### The Problem

Books need to come from multiple sources:
- **Local database**: For quick lookups, popular/cached books
- **External API**: For comprehensive coverage of millions of books

### The Solution: Dual-Source Search

The `SearchBookView` implements a **smart hybrid search** that:

1. **Queries database first** (fast, indexed)
2. **If DB fills the page**, returns immediately (most common case)
3. **If DB incomplete**, fills the gap with API results
4. **Cleans and deduplicates** API results

### Implementation Details

**Search Algorithm**:
```python
def search_books(query, page, page_size):
    # Step 1: Query database
    start = (page - 1) * page_size
    end = page * page_size
    db_books = Book.objects.filter(title__icontains=query)[start:end]
    db_results = format_results(db_books)
    
    # Step 2: Check if DB results fill the page
    if len(db_results) == page_size:
        return {"source": "db", "results": db_results}
    
    # Step 3: Fill gap with API results
    needed = page_size - len(db_results)
    api_results = query_open_library(query, needed)
    
    # Step 4: Merge and deduplicate
    combined = db_results + api_results
    return {"source": "hybrid", "results": combined[:page_size]}
```

**Benefits**:
- **Speed**: DB-only results are instant (no external API call)
- **Coverage**: API fallback provides access to millions of books
- **Efficiency**: Only calls API when necessary
- **Consistency**: Same interface regardless of source

### API Integration (Open Library)

**Endpoint Used**: `https://openlibrary.org/search.json`

**Request Parameters**:
```
q=       # Search query (book title, author, etc.)
page=    # Page number for API pagination
limit=   # Results per page
```

**Open Library Response** (example):
```json
{
  "docs": [
    {
      "key": "/works/OL45883W",
      "title": "The Hobbit",
      "author_name": ["J.R.R. Tolkien"],
      "first_publish_year": 1937,
      "subject": ["Fantasy", "Adventure", "Dragons"],
      "edition_count": 200,
      "cover_i": 5383570  // Cover ID for image construction
    }
  ]
}
```

**Data Extraction**:
```python
for item in api_response['docs']:
    book = {
        'title': item['title'],
        'author': item['author_name'][0] if item.get('author_name') else 'Unknown',
        'release_date': item.get('first_publish_year'),
        'genre': item.get('subject', [])[:3],  # First 3 subjects
        'cover': f"https://covers.openlibrary.org/b/id/{item.get('cover_i')}-M.jpg" if item.get('cover_i') else '',
        'external_id': item['key'],
        'description': ''
    }
```

**Deduplication**:
```python
existing_ids = {book.id for book in db_results}
for api_book in api_results:
    if api_book['external_id'] not in existing_ids:
        clean_books.append(api_book)  # Only add if not in DB
```

### Pagination Considerations

**Database Pagination** (slice-based):
```python
start = (page - 1) * page_size
end = page * page_size
db_books = Book.objects.filter(...)[start:end]  # Django QuerySet slicing
```

**Open Library Pagination**:
- Uses `page` parameter directly
- Doesn't align with local DB pagination
- That's why local results "fill first" — reduces API calls

**Problem**: Page numbers may not be consistent across databases:
- User asks for page 2 of "Harry Potter"
- DB has 8 results total (2 pages)
- API has 1000+ results (100+ pages)
- Page 2 in DB ≠ Page 2 in API

**Solution**: Always query DB first, only call API for "missing" results on a given page.

### Performance Notes

**Best Case** (DB has 10+ results)
- 1 database query
- 0 API calls
- Response time: ~50ms

**Worst Case** (DB has 0 results)
- 1 database query (returns empty)
- 1 API call
- Data parsing + deduplication
- Response time: ~500ms (API dependent)

**Optimization Opportunities**:
- Cache popular searches in Redis
- Pre-cache top 100 books from Open Library
- Add search indexing (e.g., full-text search in DB)
- Rate limit API calls to avoid slow external requests

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

## Bearer Tokens - Refresh and Access
- The way the logout works is that when the user clicks 'logout', the app sends the refresh token 
to the server's logout endpoint(url), server searches for the token in the database and removes it
and the server clears the secure cookie holding the refresh token and any attempt to use that refresh
token again will fail.
- Access tokens are usually short-lived bearer tokens, but refresh tokens have longer lifetimes and
can be used to generate new access tokens. Removing the refresh token on logout is the only way to 
effectively terminate the session securely.
- In typical JWT setups (like Django REST framework SimpleJWT), the server requires an Access Token to identify the user making the request, while the Refresh Token is what is actually being blacklisted or removed during logout

---

## UUID Tokens & Security {#uuid-tokens}

### What is a UUID?

A **UUID (Universally Unique Identifier)** is a 128-bit cryptographic string designed to be globally unique:

```python
import uuid
token = uuid.uuid4()  # a3d5c8e2-7f1b-4d9a-8c2e-9f3b5a1d7c4e
```

### Why Use UUIDs for Tokens?

| Property | Benefit |
|----------|---------|
| **Cryptographically random** | Can't be guessed or predicted |
| **Globally unique** | No collisions across systems |
| **Stateless** | No sequential patterns |
| **128-bit entropy** | $2^{128}$ possible combinations |

### Where Used in Azaniah

```python
# Password Reset Tokens
reset_token = str(uuid.uuid4())
cache.set(f'reset_token_{reset_token}', cache_data, timeout=600)

# Email link sent to user:
# http://localhost:3000/reset-password?token=a3d5c8e2...
```

### Security Implications

**❌ Bad (Sequential)**:
```python
# Predictable - attacker can guess next token
token_counter = 1  # Tomorrow: 2, next week: 9
```

**✅ Good (UUID)**:
```python
# Unpredictable - 1 in 2^128 chance of guessing
token = uuid.uuid4()  # a3d5c8e2-7f1b-4d9a-8c2e-9f3b5a1d7c4e
```

---

## Password Reset Flow {#password-reset-flow}

### Architecture

```
Backend                           Cache                  Frontend
────────────────────────────────────────────────────────────────

POST /password-reset/
  ├─ Generate UUID
  ├─ Store in cache ─────────────→ reset_token_abc → {email, expiry}
  ├─ Send email with link
  └─ Return 200

User clicks email link: /reset-password?token=abc

                                                 GET page
                                                 ├─ Read token from URL
                                                 └─ Show password form

POST /password-reset/confirm/
  ├─ Receive {token, new_password}
  ├─ Validate token ─────────────→ Found? Valid?
  ├─ Get email from cache
  ├─ Update Account.Password
  ├─ Update User.password (sync)
  ├─ Delete token ────────────────→ (one-time use)
  └─ Return 200
```

### Key Security Features

1. **Token Expiry**: 10-minute window via cache timeout
2. **One-Time Use**: Token deleted after use
3. **Email Verification**: User must have email access
4. **Both Models Updated**: Account + Django User stay in sync
5. **No Token in Response**: (except development mode)

### Implementation Details

**In views.py**:
```python
class ResetPasswordConfirmView(APIView):
    def post(self, request):
        # Validate token from cache
        cache_data = cache.get(f'reset_token_{token}')
        if not cache_data:
            return error: "Token expired"
        
        # Update BOTH models
        account.Password = new_password  # Auto-hashes
        account.save()
        
        user.set_password(new_password)  # Django hashing
        user.save()
        
        # Delete token (one-time use)
        cache.delete(f'reset_token_{token}')
```

---

## Gmail API Token Refresh {#gmail-api-token}

### The Problem

Gmail tokens have two types:
1. **Access Token**: Short-lived (~1 hour), used for API calls
2. **Refresh Token**: Long-lived (~6 months), used to get new access tokens

When refresh token expires:
```
from gmail_utils import send_reset_email
send_reset_email(email, token)
# ❌ Error: Invalid refresh token
```

### The Solution

**In gmail_utils.py**:
```python
def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())  # Refresh access token
                # Save updated token back to file
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                # If refresh fails, force re-auth
                flow = InstalledAppFlow.from_client_secrets_file(...)
                creds = flow.run_local_server(port=8050)
```

### When to Re-authenticate

Delete `token.json` and re-authenticate when:
- **6 months inactive** - Google auto-expires
- **User changed Google password** - Tokens invalidated
- **User revoked access** - Manual revocation
- **`token.json` corrupted** - Parse error

### Best Practice

```bash
# .gitignore
token.json
credentials.json
```

---

## Dual Password Hashing {#dual-password-hashing}

### The Problem

Azaniah uses **two different password models**:
1. **Account model**: Custom model for app-specific logic
2. **Django User model**: For JWT authentication

Both must stay in sync for login to work.

### How It Works

**During Signup**:
```python
# Both get created with hashed password
account = Account.objects.create(
    Email=email,
    Password=plain_password  # Auto-hashed in model.save()
)

user = User.objects.create_user(
    username=email,
    email=email,
    password=plain_password  # Auto-hashed by .create_user()
)
```

**During Login**:
```python
# Check 1: Custom model
if not check_password(password, account.Password):
    return error: "Invalid password"

# Check 2: Django auth
user = authenticate(username=email, password=password)
if not user:
    return error: "Invalid password"
```

**During Password Change/Reset**:
```python
# Update BOTH
account.Password = new_password
account.save()  # Auto-hashes using Account.save()

user.set_password(new_password)  # Django's secure hashing
user.save()
```

### Why Both?

| Model | Purpose |
|-------|---------|
| **Account** | Custom fields, app business logic |
| **User** | JWT token generation, Django auth |

Both needed for seamless authentication flow.

### Hash Methods

**Account model**:
```python
# Uses Django's make_password()
account.Password = make_password(password)
```

**Django User**:
```python
# Uses user.set_password()
user.set_password(password)  # PBKDF2-SHA256
```

Both use **PBKDF2-SHA256**, so they're compatible.

---

## DRF APIView: Class-Level vs Method-Level Configuration {#drf-auth-config}

### The Problem

When protecting DRF APIView endpoints with authentication, you must set `authentication_classes` and `permission_classes` at the **class level**, NOT inside methods.

### ❌ WRONG (Inside Method)

```python
class AddToLibraryView(APIView):
    def post(self, request):
        # ❌ WRONG - DRF doesn't see these here
        authentication_classes = [JWTAuthentication]
        permission_classes = [IsAuthenticated]
        
        if not request.user.is_authenticated:
            return Response({"error": "Unauthorized"}, status=401)
        
        # Rest of logic...
```

**Why it fails**:
- DRF processes authentication/permissions BEFORE calling the method
- By the time the method runs, DRF has already decided the user is unauthenticated
- Setting them inside the method is too late
- Result: **Always get 401 Unauthorized** even with valid token

### ✅ CORRECT (Class Level)

```python
class AddToLibraryView(APIView):
    # ✅ CORRECT - DRF sees these before method is called
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = UserBookSerializer(data=request.data)
        if serializer.is_valid():
            user_book = serializer.save(user=request.user)
            return Response(data, status=201)
        return Response(serializer.errors, status=400)
```

**Why it works**:
- DRF's request processing pipeline runs BEFORE the method
- Sees `authentication_classes` at class level → applies JWT auth
- Sees `permission_classes` at class level → validates user is authenticated
- If all checks pass, `request.user` is populated and method is called
- Result: **User is properly authenticated**

### DRF Request Processing Order

```
1. Request arrives
   ↓
2. DRF checks class-level authentication_classes
   └─ Looks for Authorization header
   └─ Validates JWT token
   └─ Populates request.user
   ↓
3. DRF checks class-level permission_classes
   └─ Verifies request.user satisfies permissions
   └─ If not, returns 403 Forbidden
   ↓
4. Method (get/post/put/etc) is called
   └─ By this point, authentication already done
   └─ request.user is available
```

### Common Pitfalls

**Pitfall 1: Checking Authentication in Method**
```python
# ❌ Unnecessary and won't help if classes are misconfigured
if not request.user.is_authenticated:
    return Response({"error": "..."}, status=401)

# ✅ Trust the class-level permission_classes instead
# The permission system already enforced this
```

**Pitfall 2: Setting Classes in __init__**
```python
class MyView(APIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ❌ Still wrong - too late, after class is instantiated
        self.authentication_classes = [JWTAuthentication]
        self.permission_classes = [IsAuthenticated]
```

**Pitfall 3: Forgetting to Use request.user in Serializer.save()**
```python
# ❌ Missing the actual user
user_book = serializer.save()  # user=None in many cases

# ✅ Pass the authenticated user
user_book = serializer.save(user=request.user)
```

### Template for Protected Endpoints

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status

class ProtectedView(APIView):
    # 1. ALWAYS at class level
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # 2. request.user is guaranteed to exist here
        # 3. It's only called if authentication passed
        
        serializer = MySerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save(user=request.user)
            return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Testing Protected Endpoints

**In Postman**:
1. Send request to endpoint
2. Go to **Authorization** tab
3. Select **Bearer Token** or create with `token {{access_token}}`
4. Paste your JWT access token
5. Postman automatically adds `Authorization: Bearer <token>` header
6. Send request

**In curl**:
```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
     http://localhost:8000/api/library/
```

**In JavaScript/Fetch**:
```javascript
fetch('/api/library/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
})
```

### Summary

| Aspect | Class Level | Method Level |
|--------|-------------|--------------|
| **Seen by DRF** | ✅ Yes | ❌ No |
| **Applied before method** | ✅ Yes | ❌ No |
| **request.user populated** | ✅ Yes | ❌ No |
| **Works** | ✅ Yes | ❌ No |

**Key Takeaway**: Always define `authentication_classes` and `permission_classes` as **class attributes**, not in methods.

---

## Serializer Context: When and Why You Need It {#serializer-context}

### What is Context?

**Context** is a dictionary passed to a serializer that provides additional information beyond the request data. The most important is `request`, which gives the serializer access to the authenticated user.

```python
# Without context
serializer = UserBookSerializer(data=request.data)
# serializer.context = {} (empty)

# With context
serializer = UserBookSerializer(data=request.data, context={'request': request})
# serializer.context = {'request': <Request object>}
```

### When You DON'T Need Context

**Generic serializers that don't care about the current user:**

```python
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['Email', 'First_name', 'Last_name', 'Password']
    
    def create(self, validated_data):
        # Just creates account with provided data
        # Doesn't validate ownership or check user permissions
        account = Account.objects.create(**validated_data)
        return account

# Usage - no context needed:
serializer = AccountSerializer(data=request.data)
```

**Why it works**: The serializer only creates data based on what's in the request body. It doesn't need to know WHO is creating it.

### When You DO Need Context

**Serializers that validate based on the current user:**

```python
class UserBookSerializer(serializers.ModelSerializer):
    def validate_book(self, value):
        # ❌ This will crash without context:
        request = self.context.get("request")  # Returns None if no context!
        user = request.user  # ❌ None.user → AttributeError
        
        # Check: Does THIS USER already have THIS BOOK?
        if UserBook.objects.filter(user=user, book=value).exists():
            raise serializers.ValidationError(
                "Book already exists in your library."
            )
        return value
    
    def create(self, validated_data):
        # ❌ Also needs context to get the user:
        request = self.context.get("request")
        user = request.user
        
        # Create entry linked to the current user
        user_book = UserBook.objects.create(
            user=user,
            **validated_data
        )
        return user_book

# Usage - MUST pass context:
serializer = UserBookSerializer(
    data=request.data, 
    context={'request': request}  # ✅ Pass it!
)
```

**Why it's needed**: The serializer validates **ownership** - it needs to know "does the current user already have this book?" This requires access to `request.user`.

### The Error Without Context

```python
# View creates serializer WITHOUT context
serializer = UserBookSerializer(data=request.data)  # ❌ Mistake

# Serializer tries to validate
if serializer.is_valid():  # Calls validate_book()
    # In validate_book():
    request = self.context.get("request")  # Returns None
    user = request.user  # ❌ AttributeError: 'NoneType' object has no attribute 'user'
```

### Comparison Table

| Scenario | Serializer Example | Needs Context? | Why? |
|----------|---|---|---|
| Create generic data | AccountSerializer | ❌ No | Doesn't care who creates it |
| Create user-specific data | UserBookSerializer | ✅ Yes | Needs to link to current user |
| Validate ownership | `validate_book()` checks if user has book | ✅ Yes | Must check current user's books |
| Validate permissions | "Only author can edit" | ✅ Yes | Must check who owns it |
| Build absolute URLs | `HyperlinkedRelatedField` | ✅ Yes | Needs request to build URL |
| Audit logging | "Log who created this" | ✅ Yes | Must record current user |

### Best Practice: Always Pass Context When User-Specific

Even if your current serializer doesn't use context, if it MIGHT become user-specific later, pass it:

```python
# ✅ Safe - always works
serializer = UserBookSerializer(
    data=request.data,
    context={'request': request}
)

# ❌ Fragile - breaks if you add user checks later
serializer = UserBookSerializer(data=request.data)
```

### Pattern: User-Specific Serializers

Any time you're working with data that belongs to a user, follow this pattern:

```python
class UserSpecificSerializer(serializers.ModelSerializer):
    """Any serializer that validates based on current user"""
    
    class Meta:
        model = UserModel
        fields = [...]
    
    def validate_something(self, value):
        # ✅ Get request from context
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request context missing")
        
        user = request.user
        # Now you can validate user ownership
        return value
    
    def create(self, validated_data):
        # ✅ Get user from context
        request = self.context.get("request")
        user = request.user
        
        # Create linked to user
        return UserModel.objects.create(user=user, **validated_data)

# ✅ In view: Always pass context
class UserSpecificView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = UserSpecificSerializer(
            data=request.data,
            context={'request': request}  # ← Always
        )
        if serializer.is_valid():
            serializer.save()
            return Response(...)
        return Response(serializer.errors, status=400)
```

### Summary

- **Generic serializers** (no user logic): Can skip context
- **User-specific serializers** (check ownership, permissions, audit): MUST pass `context={'request': request}`
- **Rule of thumb**: If your `validate_*()` or `create()` method accesses `request.user`, you NEED context
- **Safe default**: Always pass context, it doesn't hurt
