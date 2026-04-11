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

## Pull and Merge
- whenever you checkout to the main branch, pull always
- then git checkout "-new branch"
- merge the subsidiary branches with the main branch when work on them is complete
