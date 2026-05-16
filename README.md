# azaniah-backend
The Backend code to Azaniah Books web app.

## Recent Updates (May 13, 2026)

### 🔧 Book Model Enhancements
- **Metadata Enrichment**: Integrated Google Books API to enrich book data with missing genres, descriptions, and cover images
- **Nullable Cover Field**: `cover` field now supports NULL values for books without cover images
- **Flexible google_books_id**: Removed unique constraint to allow metadata from multiple API sources
- **Extended Descriptions**: Increased description field capacity from 15K to 250K characters

### 🌐 Dual-Source Book Search
- **Hybrid Search Strategy**: Combines Open Library API with Google Books API for comprehensive coverage
- **Smart Enrichment**: Automatically fetches missing metadata from Google Books when Open Library data is incomplete
- **Fallback Logic**: If a book lacks genres or cover image, the system calls Google Books API to fill gaps

## Features

- **User Authentication**: Email-based signup with OTP verification, Google OAuth, and JWT token management
- **Book Search**: Search books from local database and dual-API sources (Open Library + Google Books) with pagination
- **User Library**: Add books to personal library, track reading status (want to read, reading, finished)
- **Fetch Library**: Retrieve all books in user's reading library with full metadata and reading status
- **Update Library**: Update book reading status, ratings, and reviews in user's personal library
- **Delete Library** ⭐ NEW: Remove books from user's personal library
- **Rating & Reviews**: Rate books (1-5 stars) and write reviews
- **Profile Management**: Update user profile with personal details and favorite genres
- **Genre Management**: Track favorite book genres for recommendations and content filtering

## Authentication API Documentation

Base URL: `http://localhost:8000/api/auth/`

### 1. Signup (Local)
- `POST /api/auth/signup/`
- Body (JSON):
  - `email` (string, required)
  - `password` (string, required, min 8)
  - `first_name` (string, optional)
  - `last_name` (string, optional)

Response:
- `201 Created` + `{ "detail": "Account created. OTP sent to email." }`
- email has OTP code for verification

### 2. Verify OTP
- `POST /api/auth/verify-otp/`
- Body (JSON):
  - `email` (string, required)
  - `otp` (string, required)

Response:
- `200 OK` + `{ "detail": "OTP verified, account activated and Django user created." }`
- sends confirmation email with profile link

### 3. Login
- `POST /api/auth/login/`
- Body (JSON):
  - `email` (string, required)
  - `password` (string, required)

Response:
- `200 OK` on success: constructs user summary
- `403` for unverified
- `401` for invalid credentials

### 4. Google Signup
- `POST /api/auth/google-signup/`
- Body (JSON):
  - `email` (string, required)
  - `google_id` (string, required)
  - `first_name` (string, optional)
  - `last_name` (string, optional)

Response:
- `201 Created` + `{ "detail": "Google signup successful." }`
- no OTP; account is auto-verified

### 5. Profile
- `GET /api/auth/profile/?email=<email>`
- `PUT /api/auth/profile/` with body:
  - `email` (string, required)
  - `first_name`, `last_name`, `username`, `password` (optional)

Response:
- `200 OK` with profile data or update detail

## Model info
- `Azaniah/authentication/models.py` has `Account` custom user model
- `Account.verify_otp()` calls `create_django_user()` to create `django.contrib.auth.User` after verification
- `Profile` model: one-to-one relationship with Account; stores optional user details (username, phone, country, address)
- `Favourite_genres` (ManyToMany): users can select multiple genres for recommendations and friend matching
- `Genre` model: pre-defined book genres (fantasy, romance, sci-fi, mystery, etc.) with key and name fields

### Account Model
- Email (unique, required)
- First_name, Last_name (optional)
- Password (auto-hashed on save using Django's make_password)

### Profile Model
- Username, Phone, Country, Address (all optional)
- Favourite_genres (ManyToMany to Genre)
- created_at, updated_at timestamps
- Validation ensures genres are from valid GENRE_CHOICES list

### Available Genres
Action, Biography, Children, Contemporary Fiction, Dystopian, Fantasy, Graphic Novel, Historical Fiction, Horror, Literary Fiction, Mystery, Others, Religion & Spirituality, Romance, Science Fiction, Thriller & Suspense, Travel, True Crime, Young Adult

## Book Model & Search Architecture

### Book Model Fields
```python
class Book(models.Model):
    title               # CharField(max_length=300) - Book title
    author              # CharField(max_length=150) - Author name
    google_books_id     # CharField(max_length=250, null=True, blank=True) - Google Books API ID
    release_date        # IntegerField(null=True, blank=True) - Publication year
    genre               # JSONField - List of genre tags
    cover               # URLField(blank=True, null=True) - Book cover URL (CAN BE NULL)
    description         # CharField(max_length=250000) - Detailed description (expanded from 15K)
    page_count          # IntegerField(null=True, blank=True) - Number of pages
    external_id         # CharField(max_length=100, unique=True) - Primary dedup key (Open Library key)
```

**Key Design Decisions**:
- ✅ `cover` is nullable - some books from APIs don't have cover images
- ✅ `google_books_id` is NOT unique - books from different sources can share the same Google ID
- ✅ `external_id` (Open Library key) is the primary deduplication mechanism
- ✅ `description` field expanded to 250K characters to accommodate full descriptions

### Dual-API Enrichment Strategy

The search endpoint uses a two-stage enrichment process:

1. **Open Library First**: Retrieves books, genres, and basic metadata
2. **Google Books Fallback**: If genres are missing OR cover image is missing, calls Google Books API to fill gaps

**Enrichment Function: `fetch_google_book(title, author)`**
- Called when Open Library results lack genres or cover images
- Returns: `google_books_id`, `description`, `genre`, `cover`, `page_count`
- Handles NULL gracefully if API call fails

**Result: Hybrid Records**
- Book records have complete metadata from both sources
- No duplicate entries because deduplication uses `external_id`
- All books stored with proper coverage even if one API is incomplete

## Email Integration
- Gmail API integration (`gmail_utils.py`) for sending OTPs and confirmation emails
- OAuth2 authentication with credentials.json
- Service account uses Gmail API v1 with send scope
- Token auto-refresh on expiry

## Settings
- Email is currently `console.EmailBackend` for dev output (update to Gmail in production)
- `PROFILE_URL = 'http://localhost:8000/profile/'`
- JWT authentication enabled for protected endpoints
- REST framework configured with JWT token support

## Run locally
1. `python manage.py makemigrations authentication`
2. `python manage.py migrate`
3. `python manage.py runserver`

## Testing notes
- Add tests in `Azaniah/authentication/tests.py` for each endpoint with expected success and failure flows.

## Books API Documentation

Base URL: `http://localhost:8000/api/books/`

### 1. Search Books
- `GET /api/books/search/`
- Query Parameters (pass in URL, not as JSON body):
  - `q` (string, required): Search query (book title)
  - `page` (integer, required): Page number (starts at 1)
  - `page_size` (integer, optional, default: 10): Results per page

**Testing**: Since this is a GET request, parameters go directly in the URL query string:
```
GET http://localhost:8000/api/books/search/?q=harry+potter&page=1&page_size=10
```
**NOT** as raw JSON in the request body.

Response:
- `200 OK` on success with paginated results
- `400 Bad Request` if query missing or params invalid
- `503 Service Unavailable` if API unavailable

Sample Response:
```json
{
  "source": "db",
  "page": 1,
  "page_size": 10,
  "results": [
    {
      "id": 1,
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "cover": "https://example.com/cover.jpg",
      "release_date": 1937,
      "genre": ["fantasy", "adventure"]
    }
  ]
}
```

### 2. Add Book to Library
- `POST /api/books/library/`
- Auth Required: ✅ Yes (Bearer token)
- Body (JSON):
  - `book` (integer, required): Book ID from search results
  - `status` (string, required): One of `none`, `want`, `reading`, `finished`
  - `ratings` (integer, optional): 1-5 star rating
  - `review` (string, optional): User's written review

Response:
- `201 Created` on success with book added to library
- `400 Bad Request` if book already in library or invalid data
- `401 Unauthorized` if not authenticated

Example:
```json
{
  "message": "Book added to library successfully",
  "data": {
    "book": 1,
    "status": "want",
    "ratings": null,
    "review": null
  }
}
```

### 3. Fetch User Library ⭐ NEW
- `GET /api/books/library/fetch/`
- Auth Required: ✅ Yes (Bearer token)
- Purpose: Retrieve all books in the authenticated user's reading library

Response:
- `200 OK` on success with user's complete library
- `401 Unauthorized` if not authenticated

Example:
```json
{
  "message": "Library fetched successfully",
  "amount": 3,
  "books": [
    {
      "id": 1,
      "book": 5,
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "cover": "https://example.com/cover.jpg",
      "release_date": 1937,
      "genre": ["fantasy", "adventure"],
      "status": "want",
      "ratings": null,
      "review": null,
      "created_at": "2026-04-15T10:30:00Z",
      "updated_at": "2026-04-15T10:30:00Z"
    },
    {
      "id": 2,
      "book": 12,
      "title": "Harry Potter and the Philosopher's Stone",
      "author": "J.K. Rowling",
      "cover": "https://example.com/hp.jpg",
      "release_date": 1997,
      "genre": ["fantasy", "magic"],
      "status": "reading",
      "ratings": null,
      "review": null,
      "created_at": "2026-04-10T14:20:00Z",
      "updated_at": "2026-04-12T09:15:00Z"
    }
  ]
}
```

**Key Features**:
- Returns all books in user's personal library
- Books sorted by most recently added (reverse chronological)
- Includes full book details: title, author, cover, genre, release date
- Shows current reading status for each book (want, reading, finished)
- Includes user's ratings and written reviews if available
- Tracks when each book was added and last updated

### 4. Update Library Entry ⭐ NEW
- `PATCH /api/books/library/update/<userbook_id>/`
- Auth Required: ✅ Yes (Bearer token)
- Purpose: Update a book's reading status, rating, or review in the user's library
- URL Parameter: `userbook_id` (integer) - The ID of the UserBook entry to update

Request Body (JSON - all fields optional):
```json
{
  "status": "reading",
  "ratings": 4,
  "review": "Great book! Couldn't put it down."
}
```

Response:
- `200 OK` on success with updated book entry
- `404 Not Found` if book not in user's library
- `400 Bad Request` if invalid data
- `401 Unauthorized` if not authenticated

Example:
```json
{
  "message": "Book updated successfully",
  "data": {
    "id": 5,
    "book": 12,
    "title": "Harry Potter and the Philosopher's Stone",
    "author": "J.K. Rowling",
    "cover": "https://example.com/hp.jpg",
    "release_date": 1997,
    "genre": ["fantasy", "magic"],
    "status": "reading",
    "ratings": 4,
    "review": "Great book! Couldn't put it down.",
    "created_at": "2026-04-10T14:20:00Z",
    "updated_at": "2026-05-11T16:45:00Z"
  }
}
```

**Updateable Fields**:
- `status` (string): One of `none`, `want`, `reading`, `finished`
- `ratings` (integer): 1-5 star rating
- `review` (string): User's written review

**Use Cases**:
- Change reading status from "want" to "reading"
- Mark book as "finished" when done
- Add or update rating and review
- Update review text after initial addition

### 5. Delete Library Entry ⭐ NEW
- `DELETE /api/books/library/delete/<userbook_id>/`
- Auth Required: ✅ Yes (Bearer token)
- Purpose: Remove a book from the user's reading library
- URL Parameter: `userbook_id` (integer) - The ID of the UserBook entry to delete

Response:
- `204 No Content` on success (empty response body)
- `404 Not Found` if book not in user's library
- `401 Unauthorized` if not authenticated

Example Success Response:
```
HTTP 204 No Content

{
  "message": "Book removed from library successfully"
}
```

**Use Cases**:
- Remove accidental book additions
- Clean up library by removing books user no longer wants
- Delete books from "want to read" list
- Remove completed books from "finished" section

## Book Model Info

### Book Model
- `title` (CharField, max 300): Book title
- `author` (CharField, max 150): Author name
- `release_date` (IntegerField, nullable): Publication year
- `genre` (JSONField): List of genre tags (e.g., `["fantasy", "adventure"]`)
- `cover` (URLField, nullable): Book cover image URL
- `description` (CharField, max 15000): Book description
- `external_id` (CharField, unique): Open Library ID or external reference

**Storage**: Local database stores frequently searched or popular books for quick lookups

### UserBook Model - User's Reading List
- `user` (ForeignKey to User): Which user owns this entry
- `book` (ForeignKey to Book): Which book is being tracked
- `status` (CharField): One of `none`, `want`, `reading`, `finished`
- `ratings` (PositiveSmallIntegerField, nullable): 1-5 star rating or custom
- `review` (TextField, nullable): User's written review

**Constraint**: `unique_together('user', 'book')` — Each user can only have one entry per book

**Usage**:
- Track user's "want to read" list
- Store "currently reading" status
- Record completed books with ratings and reviews
- Build reading history and recommendation engine

## Pull and Merge
- whenever you checkout to the main branch, pull always
- then git checkout "-new branch"
- merge the subsidiary branches with the main branch when work on them is complete
