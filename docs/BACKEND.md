# Azaniah Backend API Documentation

**Version**: 1.5  
**Last Updated**: May 13, 2026  
**For**: Backend Developers & Frontend Developers

---

## Recent Major Updates (v1.5)

### 📚 Book Search Architecture Overhaul
- **Dual-API Integration**: Implemented Google Books API as fallback enrichment source
- **Smart Metadata Enrichment**: Automatically enriches Open Library results with missing genres and cover images from Google Books
- **Null-Safe Cover Field**: `cover` now supports NULL values for books without images

### 🔧 Database Model Changes
- **Book.cover**: Changed to `URLField(blank=True, null=True)` - now nullable
- **Book.google_books_id**: Removed `unique=True` constraint - allows duplicate IDs from different sources
- **Book.description**: Expanded field size from 15,000 to 250,000 characters
- **Book.external_id**: Now primary deduplication key (Open Library key) instead of google_books_id

### 🛠️ Code Improvements
- Added `fetch_google_book(title, author)` - Google Books enrichment function
- Added `fetch_google_books_details(title, author)` - Alternative details-only function
- Fixed BookSerializer: changed field name from `'image'` to `'cover'`
- Implemented conditional enrichment in SearchBookView

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication Overview](#authentication-overview)
3. [API Endpoints](#api-endpoints)
   - [Authentication Endpoints](#authentication-endpoints)
   - [Password Reset Endpoints](#password-reset-endpoints)
   - [Profile Endpoints](#profile-endpoints)
   - [Books API Endpoints](#books-api)
4. [Error Handling](#error-handling)
5. [Common Patterns](#common-patterns)
6. [Database Models](#database-models)

---

## Quick Start {#quick-start}

### Base URL
```
http://localhost:8000/api/
```

### Authentication Pattern

All endpoints (except signup/login) require JWT token in header:

```
Authorization: Bearer <access_token>
```

### Typical User Flow

1. **POST /auth/signup/** → Register with OTP
2. **POST /auth/verify-otp/** → Verify OTP, get JWT tokens
3. **POST /auth/login/** → Login with email + password (returns JWT tokens)
4. **GET /profile/** → Fetch profile (authenticated)
5. **PATCH /profile/** → Update profile (authenticated)
6. **POST /auth/change-password/** → Change password while logged in (authenticated)
7. **POST /auth/password-reset/** → Forgot password (generates reset email)
8. **Click email link** → Frontend page: `/reset-password?token=XXX`
9. **POST /auth/password-reset/confirm/** → Submit new password
10. **POST /auth/logout/** → Logout (blacklist tokens)

---

## Authentication Overview {#authentication-overview}

### Authentication Method

**JWT (JSON Web Token)** via `djangorestframework-simplejwt`

### Token Structure

**Response includes two tokens:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",    // Short-lived, ~5 min
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."     // Long-lived, ~24 hrs
}
```

**Using tokens:**
- `access` token: Include in every authenticated request header
- `refresh` token: Use to get new `access` token when it expires

### Password Hashing

Passwords are automatically hashed using Django's PBKDF2-SHA256:

```python
# Account model auto-hashes on save:
if self.Password and not self.Password.startswith('pbkdf2_sha256$'):
    self.Password = make_password(self.Password)
```

---

## API Endpoints {#api-endpoints}

### Authentication Endpoints {#authentication-endpoints}

#### 1. SIGNUP

**Endpoint**: `POST /auth/signup/`  
**Auth Required**: ❌ No  
**Rate Limit**: None (for now)

**Purpose**: Register a new account with email verification

**Request Body**:
```json
{
  "Email": "user@example.com",
  "First_name": "John",
  "Last_name": "Doe",
  "Password": "SecurePassword123"
}
```

**Response (200 OK)**:
```json
{
  "message": "OTP sent successfully, check your email!",
  "Email": "email"
}
```

**Possible Errors**:
```json
// Email already exists
{
  "error": "Account already exists!",
  "message": "These details already exist in our system, please sign in!"
}

// Validation failed (invalid email format, missing fields)
{
  "Email": ["Enter a valid email address."],
  "First_name": ["This field may not be blank."]
}
```

**Flow**:
1. Validates email format and required fields
2. Checks if account already exists (in Account + Django User models)
3. Generates random 6-digit OTP
4. Caches user data + OTP for 10 minutes
5. Sends OTP email asynchronously (non-blocking)

**Next Step**: Call [Verify OTP](#verify-otp)

---

#### 2. VERIFY OTP

**Endpoint**: `POST /auth/verify-otp/`  
**Auth Required**: ❌ No

**Purpose**: Verify OTP and create account

**Request Body**:
```json
{
  "Email": "user@example.com",
  "OTP": "123456"
}
```

**Response (201 CREATED)**:
```json
{
  "message": "Registration successful"
}
```

**Possible Errors**:
```json
// OTP expired (10 min window)
{
  "error": "Signup session expired or invalid email"
}

// Wrong OTP
{
  "error": "Invalid OTP"
}

// Email that was signed up elsewhere in the meantime
{
  "error": "Email already registered",
  "message": "An account with this email already exists."
}

// Missing fields
{
  "message": "Email and OTP required"
}
```

**What This Creates**:
- `Account` record (email, name, hashed password)
- `Profile` record (linked to account, ready for user details)
- `User` record (Django auth user for token generation)

**Next Step**: Call [Login](#login) or [Get Profile](#get-profile)

---

#### 3. LOGIN

**Endpoint**: `POST /auth/login/`  
**Auth Required**: ❌ No

**Purpose**: Authenticate existing user, get JWT tokens

**Request Body**:
```json
{
  "Email": "user@example.com",
  "Password": "SecurePassword123"
}
```

**Response (200 OK)**:
```json
{
  "message": "Login successful",
  "email": "user@example.com",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Possible Errors**:
```json
// Account not found
{
  "error": "Unsure if error comes from here need to test"
}

// Password incorrect
{
  "message": "Invalid Credentials"
}

// Missing email/password
{
  "message": "Email and Password are required"
}

// Django auth failed for other reasons
{
  "error": "Invalid credentials"
}
```

**What You Get**:
- `access` token: Valid for ~5-15 minutes, use for API calls
- `refresh` token: Valid for ~24 hours, use to get new `access` token

**Next Steps**:
- Use `access` token in `Authorization: Bearer <access>` header for [Profile endpoints](#profile-endpoints)
- Use `refresh` token later to get new `access` when it expires

---

#### 4. LOGOUT

**Endpoint**: `POST /auth/logout/`  
**Auth Required**: ✅ Yes (Bearer token required)

**Purpose**: Invalidate refresh token, logout user

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK)**:
```json
{
  "message": "Logout successful"
}
```

**Possible Errors**:
```json
// No token in header
{
  "detail": "Authentication credentials were not provided."
}

// Invalid/expired token
{
  "error": "Invalid or expired token"
}

// Missing refresh token in body
{
  "error": "Refresh token is required"
}
```

**After Logout**:
- `access` and `refresh` tokens are blacklisted
- User must call [Login](#login) again
- Frontend should discard tokens from storage

---

### Password Reset Endpoints {#password-reset-endpoints}

#### 5. REQUEST PASSWORD RESET

**Endpoint**: `POST /auth/password-reset/`  
**Auth Required**: ❌ No

**Purpose**: Initiate password reset, generate token, send email with reset link

**Request Body**:
```json
{
  "Email": "user@example.com"
}
```

**Response (200 OK)**:
```json
{
  "message": "Password reset link sent successfully, check your email!"
}
```

**Possible Errors**:
```json
// Email not found (security: don't reveal)
{
  "message": "If email exists, password reset link has been sent"
}

// Missing email
{
  "error": "Email is required"
}
```

**What Happens Behind the Scenes**:
1. Generates unique UUID token: `a3d5c8e2-7f1b-4d9a-8c2e-9f3b5a1d7c4e`
2. Stores token in cache with email (10-minute expiry)
3. Sends HTML email with reset link containing the token
4. Email link format: `http://localhost:3000/reset-password?token=a3d5c8e2...`

**Next Step**: User clicks email link → Frontend page loads → User enters new password

---

#### 6. CONFIRM PASSWORD RESET

**Endpoint**: `POST /auth/password-reset/confirm/`  
**Auth Required**: ❌ No

**Purpose**: Verify token and update password to new value

**Request Body**:
```json
{
  "token": "a3d5c8e2-7f1b-4d9a-8c2e-9f3b5a1d7c4e",
  "new_password": "NewPassword123"
}
```

**Response (200 OK)**:
```json
{
  "message": "Password reset successfully. You can now login with your new password.",
  "email": "user@example.com"
}
```

**Possible Errors**:
```json
// Token missing
{
  "error": "token and new_password are required"
}

// Password too short
{
  "error": "Password must be at least 8 characters long"
}

// Token expired (>10 minutes)
{
  "error": "Reset link expired or invalid. Please request a new one."
}

// Token tampered with or doesn't exist
{
  "error": "Reset link expired or invalid. Please request a new one."
}

// Account not found
{
  "error": "Account not found"
}
```

**What This Does**:
1. Validates token exists in cache
2. Gets email from cached token
3. Updates Account password (auto-hashes)
4. Deletes token from cache (one-time use only)
5. Returns success

**After Reset**:
- User can login with new password
- Old password no longer works
- Token is invalidated and can't be reused

---

### Profile Endpoints {#profile-endpoints}

All profile endpoints require authentication. Include JWT token in header:

```
Authorization: Bearer <access_token>
```

#### 7. GET PROFILE

**Endpoint**: `GET /profile/`  
**Auth Required**: ✅ Yes  
**Method**: GET

**Purpose**: Fetch authenticated user's profile with account details

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK)**:
```json
{
  "message": "Profile retrieved successfully",
  "profile": {
    "Email": "user@example.com",
    "First_name": "John",
    "Last_name": "Doe",
    "Username": "john_doe",
    "Phone": "+233501234567",
    "Country": "Ghana",
    "Address": "123 Main St, Accra",
    "Favourite_genres": ["romance", "fantasy", "sci-fi"],
    "created_at": "2026-04-09T10:30:00Z",
    "updated_at": "2026-04-10T14:22:15Z"
  }
}
```

**Read-Only Fields** (fetched from Account model):
- `Email`
- `First_name`
- `Last_name`

**Editable Fields**:
- `Username`
- `Phone`
- `Country`
- `Address`
- `Favourite_genres`

**Possible Errors**:
```json
// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Email not provided
{
  "message": "Email is required to view profile"
}

// Account not found
{
  "error": "Account not found"
}

// Profile doesn't exist
{
  "message": "Profile doesn't exist"
}
```

---

#### 8. POST PROFILE (Create/Update Full Profile)

**Endpoint**: `POST /profile/`  
**Auth Required**: ✅ Yes  
**Method**: POST

**Purpose**: Update full profile (all fields)

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "Username": "john_doe",
  "Phone": "+233501234567",
  "Country": "Ghana",
  "Address": "123 Main St, Accra",
  "Favourite_genres": ["romance", "fantasy", "sci-fi"]
}
```

**Response (200 OK)**:
```json
{
  "message": "Profile updated successfully",
  "profile": {
    "Email": "user@example.com",
    "First_name": "John",
    "Last_name": "Doe",
    "Username": "john_doe",
    "Phone": "+233501234567",
    "Country": "Ghana",
    "Address": "123 Main St, Accra",
    "Favourite_genres": ["romance", "fantasy", "sci-fi"],
    "created_at": "2026-04-09T10:30:00Z",
    "updated_at": "2026-04-10T15:00:00Z"
  }
}
```

**Possible Errors**:
```json
// Invalid favorite genre key
{
  "Favourite_genres": [
    "Object with key=invalid_genre does not exist."
  ]
}

// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Profile not found
{
  "error": "Profile not found"
}
```

---

#### 9. PATCH PROFILE (Partial Update)

**Endpoint**: `PATCH /profile/`  
**Auth Required**: ✅ Yes  
**Method**: PATCH

**Purpose**: Partially update profile (send only fields to change)

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body** (only send fields you want to update):
```json
{
  "Username": "new_username",
  "Favourite_genres": ["action", "horror", "mystery"]
}
```

**Response (200 OK)**:
```json
{
  "message": "Profile updated successfully",
  "profile": {
    "Email": "user@example.com",
    "First_name": "John",
    "Last_name": "Doe",
    "Username": "new_username",
    "Phone": "+233501234567",
    "Country": "Ghana",
    "Address": "123 Main St, Accra",
    "Favourite_genres": ["action", "horror", "mystery"],
    "created_at": "2026-04-09T10:30:00Z",
    "updated_at": "2026-04-10T15:15:00Z"
  }
}
```

**Example 1: Update Only Username**
```json
{
  "Username": "jane_smith"
}
```
Other fields remain unchanged.

**Example 2: Update Only Favorite Genres**
```json
{
  "Favourite_genres": ["sci-fi", "dystopian"]
}
```

**Example 3: Clear Favorite Genres**
```json
{
  "Favourite_genres": []
}
```

**Possible Errors**:
```json
// Genre key doesn't exist
{
  "Favourite_genres": [
    "Object with key=nonexistent_genre does not exist."
  ]
}

// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Profile not found
{
  "error": "Profile not found"
}

// Invalid field value
{
  "Phone": ["Ensure this field has no more than 20 characters."]
}
```

---

#### 10. CHANGE PASSWORD (Authenticated User Only)

**Endpoint**: `POST /auth/change-password/`  
**Auth Required**: ✅ Yes (Bearer token required)  
**Method**: POST

**Purpose**: Allow authenticated user to change their password (requires old password verification)

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "old_password": "CurrentPassword123",
  "new_password": "NewPassword456"
}
```

**Response (200 OK)**:
```json
{
  "message": "Password changed successfully"
}
```

**Possible Errors**:
```json
// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Old password incorrect
{
  "error": "Old password is incorrect."
}

// Missing fields
{
  "old_password": ["This field is required."],
  "new_password": ["This field is required."]
}

// Account not found (shouldn't happen)
{
  "error": "Account not found"
}

// Server error
{
  "error": "An error occurred while changing password"
}
```

**What Happens**:
1. Validates user is authenticated
2. Verifies old password is correct
3. Updates password in both Account and User models
4. Returns success

**After Change**:
- New password takes effect immediately
- Old password no longer works
- All existing JWT tokens remain valid (user stays logged in)

---

## Error Handling {#error-handling}

### Error Response Structure

```json
{
  "error": "Error code or message",
  "message": "Human readable explanation (optional)",
  "field_errors": {
    "field_name": ["error details"]
  }
}
```

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET, POST, PATCH |
| 201 | Created | Account successfully created |
| 400 | Bad Request | Validation error, missing fields, invalid data |
| 401 | Unauthorized | Invalid/missing token |
| 404 | Not Found | Account/Profile doesn't exist |
| 500 | Server Error | Unexpected backend error |

### Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `"auth_credentials_were_not_provided"` | Missing `Authorization` header | Add: `Authorization: Bearer <token>` |
| `"Object with key=X does not exist"` | Invalid genre key | Use valid genre keys: `romance`, `action`, `fantasy`, etc. |
| `"Email already exists"` | Email registered twice | Use different email or reset |
| `"Signup session expired"` | OTP timeout (>10 min) | Resend OTP using signup again |
| `"Invalid OTP"` | Wrong OTP code | Enter correct OTP from email |

---

## Common Patterns {#common-patterns}

### Pattern 1: Full User Signup

```
1. POST /auth/signup/
   ↓ (get OTP in email)
2. POST /auth/verify-otp/
   ↓ (get access + refresh tokens)
3. GET /profile/ (verify profile created)
```

### Pattern 2: Returning User Login

```
1. POST /auth/login/
   ↓ (get access + refresh tokens)
2. GET /profile/ (authenticated request)
3. PATCH /profile/ (update as needed)
```

### Pattern 3: Password Reset Flow

```
1. POST /auth/password-reset/ with email
   ↓
2. User checks email, clicks reset link
   ↓
3. Frontend loads: /reset-password?token=XXX
   ↓
4. Frontend reads token from URL params
   ↓
5. User enters new password in form
   ↓
6. POST /auth/password-reset/confirm/ with token + password
   ↓
7. Redirect to login page
   ↓
8. Login with new password via Pattern 2
```

### Pattern 4: Update Profile

```
1. Get token from login/signup
2. PATCH /profile/ with only fields you want to change
   ↓
3. GET /profile/ to verify updates
```

### Pattern 5: Token Refresh (Future)

```
1. access_token expires
2. POST /auth/refresh/ with refresh_token
   ↓ (get new access_token)
3. Continue using new access_token
```

### Pattern 6: Change Password (Logged In User)

```
1. User is already logged in with JWT token
2. POST /auth/change-password/ with old_password + new_password
   ↓ (requires valid old password)
3. Verify new password works
4. User remains logged in (tokens still valid)
```

### Pattern 7: Logout

```
1. POST /auth/logout/ with refresh_token in body
   ↓
2. Backend blacklists token
   ↓
3. Discard access_token and refresh_token from frontend storage
   ↓
4. Redirect to login screen
```

### Pattern 8: Service Functions Architecture (Dictionary Return)

**Philosophy**: Service functions (`services/*.py`) return raw dictionaries, not `Response` objects. Views handle HTTP response creation.

**Why this pattern?**
- **Separation of Concerns**: Service layer handles business logic, view layer handles HTTP
- **Reusability**: Service functions can be called from different views, tasks, or migrations
- **Testability**: Easier to test pure dictionary returns than Response objects

**Example from `search_books()`**:

```python
# ❌ BAD: Service returns Response
def search_books(query, page, page_size):
    return Response({"source": "db", "results": results})

# ✅ GOOD: Service returns dictionary
def search_books(query, page, page_size):
    return {"source": "db", "results": results}
```

**View Usage Pattern**:

```python
class SearchBookView(APIView):
    def get(self, request):
        # Call service function (returns dict)
        result = search_books(query, page, page_size)
        
        # View checks for errors and handles HTTP response
        if "error" in result:
            return Response({"message": result["error"]}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # View wraps service output in Response
        return Response({
            "source": result["source"],#searches the function for a dictionary field of the name "source"
            "page": page,
            "page_size": page_size,
            "results": result["results"]#searches the function for a dictionary field of the name "results"
        })
```

**Key Rule**: If a service function needs to signal an error, use `{"error": "message"}` and let the view handle the HTTP status code.

---

## Database Models {#database-models}

### Account

```python
class Account(models.Model):
    Email              # EmailField, unique
    First_name         # CharField
    Last_name          # CharField
    Password           # CharField (auto-hashed)
```

### Profile

```python
class Profile(models.Model):
    account            # OneToOneField to Account
    Username           # CharField
    Phone              # CharField
    Country            # CharField
    Address            # CharField
    Favourite_genres   # ManyToManyField to Genre
    created_at         # DateTime (auto)
    updated_at         # DateTime (auto)
```

### Genre

```python
class Genre(models.Model):
    key                # CharField, unique (e.g., 'romance')
    name               # CharField (e.g., 'Romance')
```

---

## Favorite Genres (Favourite_genres Field)

### Important: SlugRelatedField Behavior

The `Favourite_genres` field uses `SlugRelatedField`, meaning it works with genre **keys** (strings) not IDs (numbers).

**Send**: `["romance", "action", "fantasy"]`  
**NOT**: `[1, 2, 3]`

### Valid Genre Keys

```
action
biography
children
contemporary_fiction
dystopian
fantasy
graphic_novel
historical_fiction
horror
literary_fiction
mystery
others
religion_&_spirituality
romance
science_fiction
thriller_&_suspense
travel
true_crime
young_adult
```

### Favorite Genres Must Exist

Before using genres in the API, they must be populated in the database:

```bash
python manage.py populate_genres
```

This creates all 19 genres from the `GENRE_CHOICES` constant.

---

## Setup & Development

### Environment

- Django 4.x
- Django REST Framework
- djangorestframework-simplejwt (JWT auth)
- Python 3.9+

### Running the Server

```bash
cd azaniah-backend
python manage.py runserver
```

Server runs on `http://localhost:8000`

### Creating Test Users

**Postman Collections**: [See team resources]  
**Manual signup**: Use `/auth/signup/` endpoint in Postman

---

## Common Postman Setups

### Setup 1: Save Access Token Automatically

In **Login** endpoint Tests tab:

```javascript
var jsonData = pm.response.json();
pm.environment.set("access_token", jsonData.access);
pm.environment.set("refresh_token", jsonData.refresh);
```

Then use in **Authorization** header:

```
Authorization: Bearer {{access_token}}
```

### Setup 2: Environment Variables

Create Postman environment with variables:

```
base_url = https://localhost:8000/api
access_token = (saved after login)
user_email = test@example.com
```

Use in requests:
```
{{base_url}}/profile/
Authorization: Bearer {{access_token}}
```

---

## Books API {#books-api}

### Overview

The Books module provides book search functionality, combining local database results with the Open Library API for comprehensive coverage.

**Base URL**: `http://localhost:8000/api/books/`

### Search Books Endpoint

#### 1. SEARCH BOOKS

**Endpoint**: `GET /books/search/`  
**Auth Required**: ❌ No  
**Rate Limit**: None (for now)

**Purpose**: Search for books by title with dual-source results (local database + Open Library API)

**Query Parameters**:
- `q` (string, required): Book title or keyword to search for
- `page` (integer, required): Page number for pagination (starts at 1)
- `page_size` (integer, optional): Number of results per page (default: 10)

**Request Example** (Query String Format):
```
GET /books/search/?q=the%20hobbit&page=1&page_size=10
```

**Important**: Since this is a GET request, parameters go in the URL query string, **NOT** as JSON in the request body. This is not `request.data`; use `request.GET` to access parameters.

**Testing in Postman**:
- Method: GET
- URL: `http://localhost:8000/api/books/search/`
- Params tab: Add `q`, `page`, `page_size` as key-value pairs (don't use raw JSON body)

**Response (200 OK)**:
```json
{
  "source": "db",
  "page": 1,
  "page_size": 10,
  "results": [
    {
      "id": 5,
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "cover": "https://example.com/cover.jpg",
      "release_date": 1937,
      "genre": ["fantasy", "adventure"]
    },
    {
      "id": 12,
      "title": "The Hobbit: The Prelude",
      "author": "J.R.R. Tolkien",
      "cover": "https://example.com/prelude.jpg",
      "release_date": 2020,
      "genre": ["fantasy"]
    }
  ]
}
```

**Response Fields Explained**:
- `source`: Where results came from (`"db"` = database only, `"api"` = Open Library API)
- `page`: Current page number
- `page_size`: Number of results returned
- `results`: Array of book objects
  - `id`: Database ID (only present for DB results)
  - `title`: Book title
  - `author`: Author name
  - `cover`: URL to book cover image (may be empty)
  - `release_date`: Publication year (integer)
  - `genre`: List of genre tags

**Search Logic**: 
1. First, searches local database for books matching the query (case-insensitive)
2. If database has enough results to fill the page, returns immediately
3. If database results are incomplete, fills the rest from Open Library API
4. Results are ordered by edition count (popularity) when from API

**Possible Errors**:
```json
// Missing query parameter
{
  "message": "The Title of the book is required"
}

// Invalid page number (must be integer)
{
  "message": "invalid literal for int()"
}

// API service unavailable
{
  "message": "API was unable to process the request"
}
```

**HTTP Status Codes**:
- `200 OK`: Search successful, results returned
- `400 Bad Request`: Missing required parameters
- `503 Service Unavailable`: Open Library API is down and DB results incomplete

### Pagination Details

**Page-based Pagination**:
- First page: `page=1`
- Second page: `page=2`
- Results calculated: `start = (page - 1) * page_size`, `end = page * page_size`

**Example Pagination Flow**:
```
page=1, page_size=10  → Results 0-9
page=2, page_size=10  → Results 10-19
page=3, page_size=10  → Results 20-29
```

**Default Behavior**:
- `page_size` defaults to 10 if omitted
- Always use query param `page` explicitly

### Hybrid Search Strategy

**Why Two Sources?**
- **Database**: Store popular/frequently searched books for faster lookups
- **Open Library API**: Access millions of books for comprehensive coverage
- **Hybrid**: Best of both worlds — instant local results + fallback to external API

**When Each Source is Used**:
1. Database is queried first (fast, indexed)
2. If DB fills the page completely, return immediately (most common)
3. If DB has fewer results than `page_size`, query Open Library API for missing results
4. Open Library results are filtered and cleaned before returning

### Open Library Integration

The search endpoint integrates with the **Open Library API** (`https://openlibrary.org/search.json`).

**How it Works**:
- Sends search query to Open Library
- Retrieves books sorted by edition count (popularity)
- Filters out incomplete/invalid entries
- Extracts relevant fields (title, author, cover, genres)
- Removes duplicates already in database

**Limitations**:
- Cover images may not be available for all books
- Genre data comes from Open Library's subject tags (may vary)
- Release dates are estimated from first edition

### Book Model Structure

**Database Fields**:
```python
class Book(models.Model):
    title           # CharField, max 300 chars
    author          # CharField, max 150 chars
    release_date    # IntegerField (year), nullable
    genre           # JSONField (list of genre tags)
    cover           # URLField, nullable
    description     # CharField, max 15000 chars
    external_id     # CharField, unique (Open Library ID or custom)
```

**Purpose**: Store book metadata for quick local lookups and recommendations

### Frontend Integration Notes

**Example Frontend Request**:
```javascript
fetch('/api/books/search/?q=harry%20potter&page=1&page_size=15')
  .then(res => res.json())
  .then(data => {
    console.log(data.results);  // Array of book objects
    console.log(data.source);   // Where results came from
  })
```

**Pagination in UI**:
- Show `page_size` results per screen
- Add prev/next buttons that increment `page` param
- Display current page and total (estimate from API response when available)

**Filtering Results**:
- Filter by genre on frontend after fetching
- Sort by release date within results if needed
- Display cover images with fallback for missing URLs

---

#### 2. ADD BOOK TO LIBRARY

**Endpoint**: `POST /books/library/`  
**Auth Required**: ✅ Yes (Bearer token required)  
**Purpose**: Add a book to the authenticated user's reading library with status tracking

**Request Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "book": 5,
  "status": "want",
  "ratings": null,
  "review": null
}
```

**Request Body Fields**:
- `book` (integer, required): Book ID to add (get from search results)
- `status` (string, required): One of `none`, `want`, `reading`, `finished`
  - `none` - Default/no status
  - `want` - Want to read
  - `reading` - Currently reading
  - `finished` - Already finished
- `ratings` (integer, optional): 1-5 star rating (null if not rated yet)
- `review` (string, optional): User's written review (can be empty)

**Response (201 CREATED)**:
```json
{
  "message": "Book added to library successfully",
  "data": {
    "book": 5,
    "status": "want",
    "ratings": null,
    "review": null
  }
}
```

**Possible Errors**:
```json
// Book already in user's library
{
  "book": [
    "Book already exists in your library."
  ]
}

// Invalid book ID
{
  "book": [
    "Invalid pk \"999\" - object does not exist."
  ]
}

// Invalid status choice
{
  "status": [
    "\"invalid\" is not a valid choice. Expected one of: 'none', 'want', 'reading', 'finished'."
  ]
}

// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Invalid token
{
  "detail": "Given token not valid for any token type"
}
```

**Validation Rules**:
1. User must be authenticated (has valid JWT token)
2. Book must exist in database
3. User can only have ONE entry per book (enforced via `unique_together` constraint)
4. Status must be one of the choices above

**What This Creates**:
- New `UserBook` entry linking the user to the book
- Tracks user's reading status
- Allows storing ratings and reviews later
- Can be updated later via PATCH to change status/ratings

**Use Cases**:
- User finds book via search, clicks "Add to library" → creates with `status="want"`
- User starts reading → PATCH to change status to `status="reading"`
- User finishes book → PATCH to `status="finished"` and add ratings/review

**Frontend Integration**:
```javascript
// User clicks "Add to Library" after finding a book
const bookId = 5;  // From search results
const accessToken = 'eyJ0eXAiOiJKV1QiLCJhbGc...';

fetch('/api/books/library/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        book: bookId,
        status: 'want',
        ratings: null,
        review: null
    })
})
.then(res => res.json())
.then(data => {
    if (res.ok) {
        console.log('Book added successfully!');
        // Update UI (disable button, show feedback)
    } else {
        console.log('Error:', data);
        // Show error message
    }
})
```

---

#### 3. FETCH LIBRARY

**Endpoint**: `GET /books/library/fetch/`  
**Auth Required**: ✅ Yes (Bearer token required)  
**Purpose**: Retrieve all books in the authenticated user's reading library

**Request Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body**: None (this is a GET request)

**Response (200 OK)**:
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
    },
    {
      "id": 3,
      "book": 18,
      "title": "1984",
      "author": "George Orwell",
      "cover": "https://example.com/1984.jpg",
      "release_date": 1949,
      "genre": ["dystopian", "political-fiction"],
      "status": "finished",
      "ratings": 5,
      "review": "A masterpiece of dystopian fiction.",
      "created_at": "2026-03-25T08:45:00Z",
      "updated_at": "2026-04-01T16:22:00Z"
    }
  ]
}
```

**Response Fields Explained**:
- `message`: Success status message
- `amount`: Total number of books in user's library
- `books`: Array of user book objects containing:
  - `id`: UserBook entry ID (primary key)
  - `book`: Book ID (foreign key to Book model)
  - `title`, `author`, `cover`, `release_date`, `genre`: Book details (from Book model)
  - `status`: Reading status (`none`, `want`, `reading`, `finished`)
  - `ratings`: 1-5 star rating (null if not rated)
  - `review`: User's written review (can be empty)
  - `created_at`: Timestamp when book was added to library
  - `updated_at`: Timestamp of last modification

**Ordering**: Books are returned in **reverse chronological order** by `created_at` (most recently added first)

**Possible Errors**:
```json
// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Invalid token
{
  "detail": "Given token not valid for any token type"
}

// Expired token
{
  "detail": "Token is invalid or expired"
}
```

**Validation Rules**:
1. User must be authenticated (has valid JWT token)
2. Only returns books belonging to the authenticated user
3. No parameters required

**What This Returns**:
- Complete user's personal reading library
- All associated metadata (status, ratings, reviews)
- Timestamps for tracking changes

**Use Cases**:
- Load "My Library" page with all user books
- Display reading status for each book (want to read, reading, finished)
- Show user ratings and reviews
- Sync library data between devices
- Generate reading statistics

**Frontend Integration**:
```javascript
// Fetch user's library on page load
const accessToken = 'eyJ0eXAiOiJKV1QiLCJhbGc...';

fetch('/api/books/library/fetch/', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    }
})
.then(res => res.json())
.then(data => {
    console.log(`Found ${data.amount} books in library`);
    data.books.forEach(userBook => {
        console.log(`${userBook.title} - Status: ${userBook.status}`);
        // Render each book in the UI
    });
})
.catch(err => {
    console.error('Error fetching library:', err);
    // Show error message
})
```

**Example Display Logic**:
```javascript
// Separate books by reading status
const wantToRead = data.books.filter(b => b.status === 'want');
const currentlyReading = data.books.filter(b => b.status === 'reading');
const finished = data.books.filter(b => b.status === 'finished');

// Display in tabs or sections
showSection('Want to Read', wantToRead);
showSection('Currently Reading', currentlyReading);
showSection('Finished', finished);
```

---

#### 4. UPDATE LIBRARY ENTRY

**Endpoint**: `PATCH /books/library/update/<int:userbook_id>/`  
**Auth Required**: ✅ Yes (Bearer token required)  
**Purpose**: Update a book's reading status, rating, or review in the authenticated user's library

**Request Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**URL Parameters**:
- `userbook_id` (integer, required): The ID of the UserBook entry to update (get from fetch library response)

**Request Body** (all fields optional - send only what you want to update):
```json
{
  "status": "reading",
  "ratings": 4,
  "review": "Great book! Couldn't put it down."
}
```

**Request Body Fields**:
- `status` (string, optional): One of `none`, `want`, `reading`, `finished`
  - `none` - Default/no status
  - `want` - Want to read
  - `reading` - Currently reading
  - `finished` - Already finished
- `ratings` (integer, optional): 1-5 star rating (can be null)
- `review` (string, optional): User's written review (can be empty or null)

**Response (200 OK)**:
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

**Response Fields Explained**:
- Includes all UserBook data with updated fields
- `updated_at` timestamp reflects the latest modification
- All book metadata is included for frontend display

**Possible Errors**:
```json
// Book not found in user's library
{
  "message": "Book not found in your library"
}

// Invalid status choice
{
  "status": [
    "\"invalid_status\" is not a valid choice. Expected one of: 'none', 'want', 'reading', 'finished'."
  ]
}

// Invalid rating value
{
  "ratings": [
    "Ensure this value is less than or equal to 5."
  ]
}

// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Invalid token
{
  "detail": "Given token not valid for any token type"
}
```

**HTTP Status Codes**:
- `200 OK`: Book updated successfully
- `400 Bad Request`: Invalid data provided
- `404 Not Found`: UserBook entry doesn't exist or doesn't belong to user
- `401 Unauthorized`: Missing or invalid authentication token

**Validation Rules**:
1. User must be authenticated (has valid JWT token)
2. UserBook must exist and belong to the authenticated user
3. Status must be one of the valid choices (if provided)
4. Rating must be between 1-5 (if provided)
5. Only the provided fields are updated (partial update via PATCH)

**What This Updates**:
- Modifies the `UserBook` entry for the specified book
- Updates only the fields provided in the request body
- Automatically updates the `updated_at` timestamp
- Book information itself remains unchanged (only user's metadata is updated)

**Use Cases**:
- User starts reading → PATCH with `status="reading"`
- User finishes book → PATCH with `status="finished"` and add `ratings` + `review`
- User wants to rate book → PATCH with just `ratings` value
- User changes mind about a book → PATCH with `status="none"`
- User updates their review → PATCH with new `review` text

**Frontend Integration**:
```javascript
// Example 1: Update reading status when user starts reading
const userBookId = 5;  // From fetch library response
const accessToken = 'eyJ0eXAiOiJKV1QiLCJhbGc...';

fetch(`/api/books/library/update/${userBookId}/`, {
    method: 'PATCH',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        status: 'reading'
    })
})
.then(res => res.json())
.then(data => {
    if (res.ok) {
        console.log('Status updated to reading!');
        updateUI(data.data);
    } else {
        console.log('Error:', data);
    }
})
```

```javascript
// Example 2: Add rating and review after finishing book
const userBookId = 5;
const accessToken = 'eyJ0eXAiOiJKV1QiLCJhbGc...';

fetch(`/api/books/library/update/${userBookId}/`, {
    method: 'PATCH',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        status: 'finished',
        ratings: 5,
        review: 'An absolute masterpiece! Must read for everyone.'
    })
})
.then(res => res.json())
.then(data => {
    if (res.ok) {
        console.log('Book marked as finished with rating!');
        updateUI(data.data);
    }
})
```

**Advanced: Update Only Specific Fields**:
```javascript
// Update only the review without changing status or rating
fetch(`/api/books/library/update/${userBookId}/`, {
    method: 'PATCH',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        review: 'Updated review after thinking about it more.'
    })
})
```

---

#### 5. DELETE LIBRARY ENTRY

**Endpoint**: `DELETE /books/library/delete/<int:userbook_id>/`  
**Auth Required**: ✅ Yes (Bearer token required)  
**Purpose**: Remove a book from the authenticated user's personal reading library

**Request Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**URL Parameters**:
- `userbook_id` (integer, required): The ID of the UserBook entry to delete (get from fetch library response)

**Request Body**: None (this is a DELETE request)

**Response (204 NO CONTENT)**:
```
HTTP/1.1 204 No Content

{
  "message": "Book removed from library successfully"
}
```

**Response Details**:
- HTTP Status: `204 No Content` — Standard REST convention for successful deletion
- Minimal response body (just a success message)
- No book data returned (it has been deleted)

**Possible Errors**:
```json
// Book not found in user's library (or already deleted)
{
  "message": "Book not found in your library"
}

// Not authenticated
{
  "detail": "Authentication credentials were not provided."
}

// Invalid token
{
  "detail": "Given token not valid for any token type"
}
```

**HTTP Status Codes**:
- `204 No Content`: Book successfully removed from library
- `404 Not Found`: UserBook entry doesn't exist or doesn't belong to user
- `401 Unauthorized`: Missing or invalid authentication token

**Validation Rules**:
1. User must be authenticated (has valid JWT token)
2. UserBook must exist and belong to the authenticated user
3. The entire UserBook entry is deleted (cannot be partially deleted)

**What This Does**:
- Deletes the `UserBook` entry from the database
- Completely removes the user-book relationship
- Book itself remains in the Book database (can be re-added later)
- All user's data about the book (status, ratings, review) is permanently deleted

**Important**: This action is permanent. Once a book is removed from the library, all associated metadata (reading status, ratings, and reviews) are lost.

**Use Cases**:
- User accidentally added a book → Remove it from library
- User regrets adding a book → Delete it
- User wants to clean up their library → Remove unwanted entries
- User changes mind about reading a book → Delete from library

**Frontend Integration**:
```javascript
// Example 1: Remove book from library with confirmation
const userBookId = 5;  // From fetch library response
const accessToken = 'eyJ0eXAiOiJKV1QiLCJhbGc...';

// First, show confirmation dialog
if (confirm('Are you sure you want to remove this book from your library?')) {
    fetch(`/api/books/library/delete/${userBookId}/`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        }
    })
    .then(res => {
        if (res.ok || res.status === 204) {
            console.log('Book removed successfully!');
            // Remove book from UI
            removeBookFromUI(userBookId);
        } else {
            return res.json().then(data => {
                console.log('Error:', data.message);
                alert('Error: ' + data.message);
            });
        }
    })
    .catch(err => {
        console.error('Error removing book:', err);
        alert('Failed to remove book');
    })
}
```

```javascript
// Example 2: Remove book silently (no confirmation for quick delete buttons)
async function removeBookFromLibrary(userBookId, accessToken) {
    try {
        const response = await fetch(`/api/books/library/delete/${userBookId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok || response.status === 204) {
            console.log('Book removed successfully');
            return { success: true };
        } else if (response.status === 404) {
            console.log('Book not found in library');
            return { success: false, error: 'Book not found' };
        } else {
            const data = await response.json();
            return { success: false, error: data.message };
        }
    } catch (err) {
        console.error('Error:', err);
        return { success: false, error: 'Network error' };
    }
}

// Usage
const result = await removeBookFromLibrary(5, accessToken);
if (result.success) {
    // Update UI
    updateLibraryUI();
} else {
    alert(`Failed: ${result.error}`);
}
```

```javascript
// Example 3: Batch delete multiple books
async function removeMultipleBooksFromLibrary(userBookIds, accessToken) {
    const results = await Promise.all(
        userBookIds.map(id =>
            fetch(`/api/books/library/delete/${id}/`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                }
            })
        )
    );

    const successCount = results.filter(r => r.ok || r.status === 204).length;
    console.log(`Successfully deleted ${successCount} out of ${userBookIds.length} books`);
    return successCount === userBookIds.length;
}
```

---
