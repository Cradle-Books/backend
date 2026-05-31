# Azaniah Backend API Documentation

## Table of Contents
1. [Overview](#overview)
2. [How the APIs Work](#how-the-apis-work)
3. [Authentication System](#authentication-system)
4. [Base URL](#base-url)
5. [Authentication Endpoints](#authentication-endpoints)
6. [Book Endpoints](#book-endpoints)
7. [Error Handling](#error-handling)
8. [Response Formats](#response-formats)

---

## Overview

Azaniah is a book discovery and personal library management platform built with Django REST Framework. The API provides endpoints for user authentication, book searching, library management, personalized recommendations, and trending books discovery.

### Key Features:
- **User Authentication**: JWT-based authentication with email verification via OTP
- **Book Search**: Search across local database and Google Books API
- **Personal Library**: Add, update, and manage your book collection
- **Recommendations**: Get personalized book recommendations based on reading history
- **Trending Books**: Discover trending books across the platform
- **User Profile**: Manage personal information and favorite genres

---

## How the APIs Work

### Architecture Overview

The Azaniah backend follows a **Service-Oriented Architecture** pattern:

1. **Views Layer**: Handles HTTP requests and responses
2. **Serializers Layer**: Validates and converts data between API and models
3. **Service Layer**: Contains business logic separate from HTTP concerns
4. **Models Layer**: Database schema and ORM definitions

### Request Flow

```
Client Request
    ↓
URL Router (urls.py)
    ↓
View (APIView)
    ↓
Serializer (validation)
    ↓
Service Function (business logic)
    ↓
Database/External API
    ↓
Response (JSON)
    ↓
Client
```

### Key Concepts

**1. Stateless API with JWT Authentication**
- Each request includes a JWT token in the Authorization header
- The server doesn't store session state
- Tokens expire after a set time and can be refreshed

**2. Request Validation**
- All API inputs are validated by serializers before reaching business logic
- Invalid requests return detailed error messages with 400 status codes

**3. Resource-Based Design**
- URLs represent resources (books, users, libraries)
- HTTP methods (GET, POST, PATCH, DELETE) define operations
- Responses include meaningful status codes

**4. Pagination**
- Search results support pagination with `page` and `page_size` parameters
- Default page size is 10 results per request

**5. Relationship Management**
- User-Book relationships stored in `UserBook` model
- Enables tracking reading status, ratings, and reviews per user
- Unique constraint ensures each user can only add a book once

---

## Authentication System

### JWT (JSON Web Token) Flow

1. **User Signs Up** → OTP sent via email
2. **User Verifies OTP** → Account created, can now login
3. **User Logs In** → Receives `access` and `refresh` tokens
4. **Access Token** → Used to authenticate subsequent API requests (short-lived, ~5 minutes)
5. **Refresh Token** → Used to get a new access token when expired (long-lived, ~24 hours)
6. **User Logs Out** → Refresh token blacklisted/discarded

### Token Usage

Include in request headers:
```
Authorization: Bearer <access_token>
```

---

## Base URL

```
http://localhost:8000/api
```

All endpoints are prefixed with this base URL.

---

## Authentication Endpoints

### 1. Sign Up (Create Account)

**Endpoint:** `POST /auth/signup/`

**Purpose:** Create a new user account and send OTP verification email

**Request Body:**
```json
{
  "Email": "user@example.com",
  "First_name": "John",
  "Last_name": "Doe",
  "Password": "SecurePassword123"
}
```

**Response (200 OK):**
```json
{
  "message": "OTP sent successfully, check your email!",
  "Email": "email"
}
```

**Error Responses:**
- `400 Bad Request` - Email already exists or validation errors
  ```json
  {
    "error": "Account already exists!",
    "message": "These details already exist in our system, please sign in!"
  }
  ```

**Requirements:**
- Email must be unique
- Password must be at least 8 characters
- Email will receive an OTP code automatically

---

### 2. Verify OTP

**Endpoint:** `POST /auth/verify-otp/`

**Purpose:** Verify OTP sent to email and complete account registration

**Request Body:**
```json
{
  "Email": "user@example.com",
  "OTP": "123456"
}
```

**Response (201 Created):**
```json
{
  "message": "Registration successful"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid OTP or email
  ```json
  {
    "error": "Invalid OTP"
  }
  ```
- `400 Bad Request` - Email already registered during signup
  ```json
  {
    "error": "Email already registered",
    "message": "An account with this email already exists. Please sign up instead."
  }
  ```

**Notes:**
- OTP is valid for 10 minutes after signup
- Creates both Account and Profile records automatically
- Creates Django User for authentication backend

---

### 3. Login

**Endpoint:** `POST /auth/login/`

**Purpose:** Authenticate user and receive JWT tokens

**Request Body:**
```json
{
  "Email": "user@example.com",
  "Password": "SecurePassword123"
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",
  "email": "user@example.com",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
  ```json
  {
    "error": "Invalid credentials"
  }
  ```
- `400 Bad Request` - Missing email or password
  ```json
  {
    "message": "Email and Password are required"
  }
  ```

**Usage:**
- Store both tokens securely on client
- Use `access` token for API requests
- Use `refresh` token to get new access tokens when expired

---

### 4. Logout

**Endpoint:** `POST /auth/logout/`

**Purpose:** Log out user and invalidate refresh token

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
  "message": "Logout successful"
}
```

**Error Responses:**
- `400 Bad Request` - Refresh token missing or invalid
  ```json
  {
    "error": "Invalid or expired token"
  }
  ```

---

### 5. Get Profile

**Endpoint:** `GET /auth/profile/`

**Purpose:** Retrieve authenticated user's complete profile

**Authentication:** Required (Bearer token)

**Query Parameters:** None for authenticated request

**Response (200 OK):**
```json
{
  "message": "Profile retrieved successfully",
  "profile": {
    "Email": "user@example.com",
    "First_name": "John",
    "Last_name": "Doe",
    "Username": "johndoe",
    "Phone": "+1234567890",
    "Country": "United States",
    "Address": "123 Main St, City, State",
    "Favourite_genres": ["romance", "fantasy", "mystery"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:30Z"
  }
}
```

**Error Responses:**
- `404 Not Found` - Account doesn't exist
  ```json
  {
    "error": "Account not found"
  }
  ```

---

### 6. Update Profile (POST)

**Endpoint:** `POST /auth/profile/`

**Purpose:** Create or update user profile with additional information

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "Username": "johndoe",
  "Phone": "+1234567890",
  "Country": "United States",
  "Address": "123 Main St",
  "Favourite_genres": ["fantasy", "romance", "mystery"]
}
```

**Response (200 OK):**
```json
{
  "message": "Profile updated successfully",
  "profile": {
    "Email": "user@example.com",
    "First_name": "John",
    "Last_name": "Doe",
    "Username": "johndoe",
    "Phone": "+1234567890",
    "Country": "United States",
    "Address": "123 Main St",
    "Favourite_genres": ["fantasy", "romance", "mystery"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T15:45:30Z"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid genre values
- `404 Not Found` - Profile not found

---

### 7. Partially Update Profile (PATCH)

**Endpoint:** `PATCH /auth/profile/`

**Purpose:** Update specific profile fields without affecting others

**Authentication:** Required (Bearer token)

**Request Body (any of these fields):**
```json
{
  "Username": "newusername",
  "Phone": "+9876543210",
  "Favourite_genres": ["horror", "thriller", "science_fiction"]
}
```

**Response (200 OK):**
```json
{
  "message": "Profile updated successfully",
  "profile": { /* updated profile data */ }
}
```

**Notes:**
- Only provide the fields you want to update
- Favourite_genres should be a list of genre keys
- Other fields remain unchanged

---

### 8. Reset Password (Request)

**Endpoint:** `POST /auth/password-reset/`

**Purpose:** Initiate password reset process and send email with reset token

**Authentication:** Not required

**Request Body:**
```json
{
  "Email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "Password reset link sent successfully, check your email!",
  "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Notes:**
- Returns success message even if email doesn't exist (for security)
- Email contains reset link: `http://localhost:3000/reset-password?token=<UUID>`
- Token is valid for 10 minutes
- Token included in response for testing (remove in production)

---

### 9. Reset Password (Confirm)

**Endpoint:** `POST /auth/password-reset/confirm/`

**Purpose:** Complete password reset with new password

**Authentication:** Not required

**Request Body:**
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "new_password": "NewSecurePassword123"
}
```

**Response (200 OK):**
```json
{
  "message": "Password reset successfully. You can now login with your new password.",
  "email": "user@example.com"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid or expired token
  ```json
  {
    "error": "Reset link expired or invalid. Please request a new one."
  }
  ```
- `400 Bad Request` - Password too short
  ```json
  {
    "error": "Password must be at least 8 characters long"
  }
  ```

---

### 10. Change Password

**Endpoint:** `POST /auth/change-password/`

**Purpose:** Change password for authenticated user (requires current password)

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "old_password": "CurrentPassword123",
  "new_password": "NewPassword456",
  "confirm_password": "NewPassword456"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Error Responses:**
- `400 Bad Request` - Old password incorrect
  ```json
  {
    "error": "Old password is incorrect."
  }
  ```
- `400 Bad Request` - Passwords don't match or too short
  ```json
  {
    "error": "errors from serializer"
  }
  ```

**Requirements:**
- New password must be at least 8 characters
- New password and confirm_password must match

---

## Book Endpoints

### 1. Search Books

**Endpoint:** `GET /books/search/`

**Purpose:** Search for books across database and Google Books API

**Authentication:** Not required

**Query Parameters:**
- `q` (required): Search query (book title)
- `page` (required): Page number (starts at 1)
- `page_size` (optional): Results per page (default: 10)

**Example Request:**
```
GET /books/search/?q=harry+potter&page=1&page_size=10
```

**Response (200 OK):**
```json
{
  "message": "Search completed successfully",
  "source": "mixed",
  "page": 1,
  "page_size": 10,
  "results": [
    {
      "id": 1,
      "title": "Harry Potter and the Philosopher's Stone",
      "author": "J.K. Rowling",
      "genre": ["fantasy", "young_adult"],
      "cover": "https://example.com/cover.jpg",
      "description": "A young wizard's first year at magic school...",
      "release_date": 1997,
      "page_count": 309,
      "external_id": "hp_1",
      "google_books_id": "10_7zNECQYoC"
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request` - Query parameter missing
  ```json
  {
    "message": "The Title of the book is required"
  }
  ```
- `503 Service Unavailable` - External API error
  ```json
  {
    "message": "Error message from API"
  }
  ```

**Notes:**
- Returns results from local database first
- Falls back to Google Books API if needed
- `source` can be: "db", "google_books", or "mixed"

---

### 2. Get Book Detail

**Endpoint:** `GET /books/book/<book_id>/`

**Purpose:** Get detailed information about a specific book

**Authentication:** Not required

**URL Parameters:**
- `book_id`: Numeric ID of the book

**Example Request:**
```
GET /books/book/1/
```

**Response (200 OK):**
```json
{
  "id": 1,
  "title": "Harry Potter and the Philosopher's Stone",
  "author": "J.K. Rowling",
  "genre": ["fantasy", "young_adult"],
  "cover": "https://example.com/cover.jpg",
  "description": "A young wizard discovers he's a wizard and attends Hogwarts School of Witchcraft and Wizardry...",
  "release_date": 1997,
  "page_count": 309,
  "external_id": "hp_1",
  "google_books_id": "10_7zNECQYoC"
}
```

**Error Responses:**
- `404 Not Found` - Book doesn't exist
  ```json
  {
    "message": "Book not found"
  }
  ```

---

### 3. Add Book to Library

**Endpoint:** `POST /books/library/`

**Purpose:** Add a book to user's personal library

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "book": 1,
  "status": "want",
  "ratings": null,
  "review": null
}
```

**Status Options:**
- `"want"` - Want to read
- `"reading"` - Currently reading
- `"finished"` - Finished reading

**Response (201 Created):**
```json
{
  "message": "Book added to library successfully",
  "data": {
    "id": 5,
    "book": 1,
    "status": "want",
    "ratings": null,
    "review": null,
    "created_at": "2024-01-20T10:30:45Z",
    "updated_at": "2024-01-20T10:30:45Z"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Book already in library
  ```json
  {
    "book": ["Book already exists in your library."]
  }
  ```
- `400 Bad Request` - Invalid book ID or status

---

### 4. Fetch User's Library

**Endpoint:** `GET /books/library/fetch/`

**Purpose:** Get all books in user's library, sorted by most recent

**Authentication:** Required (Bearer token)

**Query Parameters:** None

**Response (200 OK):**
```json
{
  "message": "Library fetched successfully",
  "amount": 15,
  "books": [
    {
      "id": 5,
      "book": 1,
      "status": "reading",
      "ratings": 4,
      "review": "Amazing book, couldn't put it down!",
      "created_at": "2024-01-20T10:30:45Z",
      "updated_at": "2024-01-21T14:22:10Z"
    },
    {
      "id": 4,
      "book": 2,
      "status": "finished",
      "ratings": 5,
      "review": "Best series ever!",
      "created_at": "2024-01-18T09:15:30Z",
      "updated_at": "2024-01-18T09:15:30Z"
    }
  ]
}
```

**Notes:**
- Books are sorted by newest first (by `created_at`)
- Shows the count of books in library
- Returns all relevant metadata for each book

---

### 5. Update Book in Library

**Endpoint:** `PATCH /books/library/update/<userbook_id>/`

**Purpose:** Update reading status, rating, or review of a book

**Authentication:** Required (Bearer token)

**URL Parameters:**
- `userbook_id`: ID of the UserBook relationship (not the book ID)

**Request Body (partial update):**
```json
{
  "status": "finished",
  "ratings": 5,
  "review": "Absolutely brilliant! One of the best books I've read."
}
```

**Response (200 OK):**
```json
{
  "message": "Book updated successfully",
  "data": {
    "id": 5,
    "book": 1,
    "status": "finished",
    "ratings": 5,
    "review": "Absolutely brilliant! One of the best books I've read.",
    "created_at": "2024-01-20T10:30:45Z",
    "updated_at": "2024-01-21T15:45:20Z"
  }
}
```

**Error Responses:**
- `404 Not Found` - Book not in user's library
  ```json
  {
    "message": "Book not found in your library"
  }
  ```
- `400 Bad Request` - Invalid rating (must be 1-5)

**Notes:**
- Only update the fields you want to change
- Rating must be between 1 and 5 (or null)
- Can update any combination of status, ratings, or review

---

### 6. Delete Book from Library

**Endpoint:** `DELETE /books/library/delete/<userbook_id>/`

**Purpose:** Remove a book from user's personal library

**Authentication:** Required (Bearer token)

**URL Parameters:**
- `userbook_id`: ID of the UserBook relationship

**Response (204 No Content):**
```
(Empty body)
```

**Error Responses:**
- `404 Not Found` - Book not in user's library
  ```json
  {
    "message": "Book not found in your library"
  }
  ```

---

### 7. Get User Profile (Books)

**Endpoint:** `GET /books/profile/`

**Purpose:** Get user's reading statistics and profile information

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "user": "user@example.com",
  "total_books": 25,
  "want_to_read": 8,
  "currently_reading": 3,
  "finished_reading": 14,
  "average_rating": 4.2,
  "favorite_genres": ["fantasy", "mystery", "romance"],
  "reading_timeline": {
    "2024": 12,
    "2023": 13
  }
}
```

**Notes:**
- Shows comprehensive reading statistics
- Includes breakdown by reading status
- Average rating calculated from rated books
- Reading timeline shows books finished by year

---

### 8. Get Trending Books

**Endpoint:** `GET /books/trending/`

**Purpose:** Get trending books across all users

**Authentication:** Not required

**Query Parameters:** None

**Response (200 OK):**
```json
{
  "message": "Trending books retrieved successfully",
  "trending_books": [
    {
      "id": 1,
      "title": "Harry Potter and the Philosopher's Stone",
      "author": "J.K. Rowling",
      "cover": "https://example.com/cover.jpg",
      "score": 95,
      "users_count": 342
    },
    {
      "id": 5,
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "cover": "https://example.com/cover2.jpg",
      "score": 88,
      "users_count": 278
    }
  ]
}
```

**Notes:**
- Books ranked by engagement (users who added them, ratings, etc.)
- Shows score and user count for each book
- No authentication required to view

---

### 9. Get Recommendations

**Endpoint:** `GET /books/recommendations/`

**Purpose:** Get personalized book recommendations based on user's reading history and favorite genres

**Authentication:** Required (Bearer token)

**Query Parameters:** None

**Response (200 OK):**
```json
{
  "message": "Recommendations retrieved successfully",
  "recommendations": [
    {
      "id": 12,
      "title": "Mistborn: The Final Empire",
      "author": "Brandon Sanderson",
      "genre": ["fantasy", "science_fiction"],
      "cover": "https://example.com/cover.jpg",
      "description": "In a world of ash and darkness...",
      "reason": "Based on your love of fantasy books"
    },
    {
      "id": 15,
      "title": "The Name of the Wind",
      "author": "Patrick Rothfuss",
      "genre": ["fantasy", "literary_fiction"],
      "cover": "https://example.com/cover2.jpg",
      "description": "A man looks back on his extraordinary life...",
      "reason": "Similar to books you've already read"
    }
  ]
}
```

**Algorithm Factors:**
- User's favorite genres
- Books with similar genres to their finished/reading books
- High-rated books in their preferred genres
- User profile settings

---

## Error Handling

### Standard Error Response Format

All errors follow this structure:

```json
{
  "error": "Error type or message",
  "detail": "Additional details (if applicable)"
}
```

### HTTP Status Codes

| Status Code | Meaning | Common Scenarios |
|---|---|---|
| **200** | OK | Successful GET or POST request |
| **201** | Created | Successfully created a new resource (signup, add to library) |
| **204** | No Content | Successful DELETE request |
| **400** | Bad Request | Invalid input, missing required fields, validation errors |
| **401** | Unauthorized | Missing or invalid authentication token |
| **404** | Not Found | Resource doesn't exist (book not found, user not found) |
| **500** | Internal Server Error | Server-side error |
| **503** | Service Unavailable | External API unavailable (Google Books API down) |

### Common Error Scenarios

**Missing Authentication Token:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Invalid Token:**
```json
{
  "detail": "Given token not valid for any token type"
}
```

**Token Expired:**
```json
{
  "detail": "Token is invalid or expired"
}
```

**Validation Error:**
```json
{
  "field_name": ["Error message for this field"],
  "another_field": ["Multiple errors possible", "Second error"]
}
```

---

## Response Formats

### Standard Success Response

Most successful responses include a message and data:

```json
{
  "message": "Operation completed successfully",
  "data": { /* resource data */ }
}
```

### Paginated Responses

Search results are paginated:

```json
{
  "message": "Search completed successfully",
  "page": 1,
  "page_size": 10,
  "results": [
    { /* book data */ }
  ]
}
```

### Timestamp Format

All timestamps are in ISO 8601 format with UTC timezone:
```
2024-01-20T15:45:30Z
```

---

## Testing the API

### Using cURL

**Sign up:**
```bash
curl -X POST http://localhost:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "Email": "user@example.com",
    "First_name": "John",
    "Last_name": "Doe",
    "Password": "SecurePassword123"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "Email": "user@example.com",
    "Password": "SecurePassword123"
  }'
```

**Authenticated Request:**
```bash
curl -X GET http://localhost:8000/api/books/library/fetch/ \
  -H "Authorization: Bearer <access_token>"
```

### Using Postman

1. Create a new collection
2. Set up environment variables:
   - `base_url`: `http://localhost:8000/api`
   - `access_token`: (updated after login)
   - `refresh_token`: (updated after login)
3. Use `{{base_url}}` and `{{access_token}}` in requests
4. After login, extract tokens from response and save to variables

### Using Thunder Client or REST Client

**Example .http file:**
```http
@baseUrl = http://localhost:8000/api
@accessToken = your_token_here

### Search Books
GET {{baseUrl}}/books/search/?q=harry+potter&page=1

### Fetch Library
GET {{baseUrl}}/books/library/fetch/
Authorization: Bearer {{accessToken}}
```

---

## Rate Limiting & Best Practices

### Recommendations

1. **Cache responses** on the client side when possible
2. **Paginate large requests** using `page_size` parameter
3. **Implement exponential backoff** for retries
4. **Store tokens securely** - never log them
5. **Refresh tokens before expiry** to prevent 401 errors
6. **Validate all user inputs** on client side before sending

### Performance Tips

- Use smaller `page_size` values to reduce response time
- Cache search results locally for repeated queries
- Batch multiple read operations when possible
- Implement request throttling to avoid overwhelming the server

---

## Support & Troubleshooting

### Common Issues

**"Token is invalid or expired"**
- Solution: Use the refresh token to get a new access token or log in again

**"Book not found in your library"**
- Solution: Ensure you're using the correct `userbook_id` from the fetch library response

**"Email already exists"**
- Solution: Use a different email or use the login endpoint if you already have an account

**"Invalid OTP"**
- Solution: Check the email for the correct OTP, make sure it hasn't expired (10 minutes)

For more help, check the server logs or contact the development team.
