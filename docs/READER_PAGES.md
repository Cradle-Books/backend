# My Shelf, Profile, and Settings

The `frontend_1` routes `/my-shelf`, `/profile`, and `/settings` use the existing
JWT-protected Cradle endpoints. They follow `design/my-shelf.png`,
`design/profile.png`, and `design/settings.png`, using the existing reader shell.
No production account data is embedded in the UI.

## Profile preferences and visibility

The frontend loads `GET /api/auth/profile/` and reads its `profile` object.
Personal information is saved separately from preferences so one form cannot
overwrite an unsaved draft in the other.

```http
PATCH /api/auth/profile/
Authorization: Bearer <access-token>
Content-Type: application/json

{"privacy":"private","Favourite_genres":["fantasy","romance"]}
```

The backend's existing `ProfileSerializer` accepts exactly `public` or `private`.
`Favourite_genres` contains stored `Genre.key` values, not the display labels.
The successful PATCH returns the updated `profile`; the frontend updates its
query cache and the visibility badge from that response. Saving personal
information refreshes session statistics so the updated display name appears
throughout the reader shell. `Email` is read-only.

Privacy uses the existing follow feature:

| Preference | A new follow request |
| --- | --- |
| `public` | Becomes accepted immediately |
| `private` | Becomes pending; the recipient must approve it |

Switching to private does not remove existing followers. The public reader
endpoint still exposes the basic username, privacy, and relationship metadata.
The control does not promise to hide every part of the account. Reading interests
are saved preferences; the current recommendation algorithm still uses genres
from reading/finished books rather than these preference values.

## Available genre keys

Added `GET /api/auth/genres/`, without authentication, to list the actual stored
choices accepted by the profile serializer:

```json
{
  "genres": [
    {"key": "fantasy", "name": "Fantasy"},
    {"key": "romance", "name": "Romance"}
  ]
}
```

This is an example; the response is sorted by name and reflects the database.
The endpoint does not insert genres. An empty table returns `{"genres":[]}` and
the frontend explains that no interests are available. Unknown keys in a profile
update are rejected by the existing serializer.

The backend must be redeployed with this route for the new genre picker to load.
This change adds no database migration. Existing migrations, including profile
privacy, must already be applied in the deployed environment.

## My Shelf

| Action | Request |
| --- | --- |
| Load shelf | `GET /api/books/library/fetch/` |
| Change reading status | `PATCH /api/books/library/update/<entry_id>/` with `status` |
| Rate or clear rating | Same PATCH with `ratings: 1..5` or `ratings: null` |
| Remove after confirmation | `DELETE /api/books/library/delete/<entry_id>/` |

Updates use the `UserBook` entry ID, not the book ID. Links to book details use
the nested book ID. Allowed statuses are `want`, `reading`, and `finished`.
`ratings` is the user's shelf rating, separate from the book's `average_rating`.

The shelf endpoint returns the complete current library, so status filters,
title/author search, counts, and sorting happen locally. The Recently Added sort
uses `created_at`; it is not a claim about when a book was finished. Dashboard
links such as `/my-shelf?status=finished` select the corresponding initial view.
There are no fabricated reading percentages or unsupported TBR statuses.

Successful mutations invalidate library, recommendations, and trending queries,
then refresh session statistics. Failures remain visible and do not claim success.

## Settings

Password changes send `old_password`, `new_password`, and `confirm_password` to
`POST /api/auth/change-password/`. Client-side confirmation and an 8-character
minimum complement backend validation. Password inputs clear after success.
Logout reuses the existing logout flow, including its local-clear fallback.

Theme (light/dark/system) and book-description text size are saved to
`localStorage` under `cradle.appearance`, with no credentials. They are browser
preferences, not account settings synced across devices. The system option tracks
OS color-scheme changes; browser storage events update other tabs. Text size
changes descriptions, not all interface labels. Storage failures are shown to
the user. Appearance is applied after hydration, so a brief default-theme flash
can occur during initial load.

Notification toggles are disabled and labelled unavailable because no preference
API exists. The UI does not claim to save reading goals, linked accounts, profile
photos, or activity-sharing preferences that the backend does not support.

## Validation and local browser checks

Backend checks:

```powershell
$env:DATABASE_URL = ''
../.venv/Scripts/python.exe manage.py test Azaniah.authentication.test_reader_preferences Azaniah.follow Azaniah.books
```

Result: 29 passed, 5 unrelated search-simulation checks skipped without their
simulation URL. Tests exercise actual Django endpoints with an isolated test
database, including privacy changes followed by pending/accepted follows,
authentication, invalid privacy, stored genre keys, shelf mutations, and password
changes. A missing-profile GET was also corrected to return 404 instead of
referencing an unassigned local variable in its exception handler.

Frontend checks: `npm.cmd run typecheck` and `npm.cmd run build`.

The saved browser script is `scripts/check_reader_pages.cjs`. It drives real
frontend pages through Chrome DevTools against the local Postman simulation:

```powershell
postman simulation run postman/simulations/reader-pages.sim.yaml --port 4906 --output ndjson --no-history
```

In `frontend_1`, start a separate preview:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL = 'http://127.0.0.1:4906/cradle'
$env:CRADLE_NEXT_DIST_DIR = '.next-reader-preview'
npm.cmd run dev -- --port 3104
```

Use an isolated Chrome session with remote debugging on port 9231 and a dedicated
temporary user-data directory, then run from `backend`:

```powershell
New-Item -ItemType Directory -Force .reader-preview
node scripts/check_reader_pages.cjs
```

The browser checks passed shelf search, status/rating updates and removal;
profile edits and persistent private visibility/genres; theme/text-size
persistence; disabled notification controls; password failures/success; and
390px/768px layouts. Screenshots were visually inspected. Simulation logs
confirmed the requests reached the mock. The mock comes from this repository's
views and serializers and uses synthetic data; the backend itself was verified
separately by Django tests. This does not verify deployed CORS or production data.
Stop owned preview processes and restore any preview-generated Next configuration
before committing.
