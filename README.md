# azaniah-backend
The Backend code to Azaniah Books web app.

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
