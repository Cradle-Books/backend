# Community and book-reader activity

`frontend_1` now connects `/community` to the follow app. The layout follows
`design/community.png`; its working tabs are Find Readers, Following, Followers,
and Requests. Posts, discussions, and events are labelled as future work because
there is no corresponding backend API. The sidebar shows actual followers the
user can follow back, not invented suggested accounts.

## Follow API contract

All requests below require the existing JWT bearer token:

| UI action | API request |
| --- | --- |
| Find an exact username | `GET /api/auth/users/?username=Amina` |
| Load accepted connections and outgoing requests | `GET /api/auth/follows/` |
| Load incoming pending requests | `GET /api/auth/follow-requests/` |
| Follow or request to follow a reader | `POST /api/auth/follow/` with `{"following":12}` |
| Approve incoming request | `POST /api/auth/follow-requests/<request_id>/accept/` |
| Decline incoming request | `POST /api/auth/follow-requests/<request_id>/deny/` |
| Unfollow or cancel an outgoing request | `DELETE /api/auth/following/<relationship_id>/` |

Search is exact and case-insensitive, returns at most one reader, and excludes
the current user. An initial `@` is stripped by the search form. A search for a
partial username does not list all matching readers. Reader links use
`/community?reader=<URL-encoded-handle>` to open this lookup directly.

Public profiles accept follows immediately. Private profiles create pending
requests; pending is never displayed as an accepted follow. Accept/decline
requires a request addressed to the authenticated user. Delete requires an
outgoing relationship owned by that user. The frontend uses actual relationship
IDs for these operations, never substitutes a user ID, and asks for confirmation
before unfollowing an accepted reader.

The connections endpoint now also returns `outgoing_pending`:

```json
{
  "followers": [],
  "following": [],
  "outgoing_pending": [
    {"id": 81, "user_id": 12, "username": "Amina", "state": "pending"}
  ]
}
```

This additive field lets users see and cancel sent requests without treating
them as accepted follows. Existing consumers can still read the original arrays.
The profile counts continue to count only accepted followers/following.

Successful actions refetch connection lists, incoming requests, reader-search
state, and profile connection counts. Buttons are disabled while a mutation is
pending. Failed requests display errors rather than changing the UI to a false
success. Guests receive a sign-in link that preserves the selected reader.

## Book-detail reader activity

`GET /api/books/book/<book_id>/` already returned `number_of_readers` and
`recent_activity`; the old frontend normalizer discarded those fields. The new
detail page retains them and displays a Readers & recent activity section.

```json
{
  "number_of_readers": 2,
  "recent_activity": [
    {
      "user": "Amina",
      "user_id": 12,
      "status": "reading",
      "status_changed_at": "2026-10-25T10:00:00Z"
    },
    {
      "user": "Tunde",
      "user_id": 13,
      "status": "finished",
      "status_changed_at": "2026-10-24T10:00:00Z"
    }
  ]
}
```

This example shows the activity fields only; the real response still includes
the book metadata, including `page_count`. The frontend maps page_count to
pageCount, number_of_readers to readerCount, and recent_activity to recentActivity.
Missing optional activity fields in older responses produce an empty activity
list without breaking the rest of the detail page.

Product decision: activity includes **both public and private profiles**, as
confirmed by the user. Private visibility continues to control new follow
approval; it does not hide these shelf updates. The count includes all saved
UserBook relationships, including Want to Read, so it is labelled reading
shelves rather than completed readers or currently reading users.

Activity is the most recent shelf/status update from up to five UserBook rows,
not a history of every interaction. It is not a comments, likes, reviews, or
rating feed. Rows are ordered by status_changed_at, falling back to created_at
for initial shelf additions, with primary key as a stable tie-breaker. The
response's status_changed_at contains that effective activity timestamp.

Previously, `user` used `Django User.username`, which can contain the sign-in
email in this application. It now resolves to `Profile.Username`, falling back
to `Account.Username`. Non-email Django usernames are allowed as a legacy
fallback when no profile exists. Empty or email-like unresolved handles are
omitted; email addresses are never used as activity labels. Consequently the
displayed activity list can have fewer than five entries even when more shelf
relationships exist. The count is independent of that display filtering.

Profile handles are resolved in one batched lookup. For nonempty activity, the
activity service uses two database queries regardless of the five-row window,
avoiding a separate profile lookup per reader. Activity links open Community's
reader lookup; a signed-in user's own activity links to `/profile` instead.
Shelf/status mutations now invalidate book-detail queries to refresh reader
counts and activity.

## Deployment and checks

Deploy both backend and frontend. These changes need no database migration:
the backend adds safe activity handles/user IDs and outgoing pending requests;
the frontend consumes them. Existing privacy migrations must already be applied.

Backend checks:

```powershell
$env:DATABASE_URL = ''
../.venv/Scripts/python.exe manage.py test Azaniah.books Azaniah.follow
```

The books/follow suite passed 29 tests with five unrelated upstream-search
simulation tests skipped. After the creation-time fallback was added, all five
book-activity tests passed again, including the new timestamp test. They verify
public/private inclusion, safe handles and IDs, page_count preservation, empty
activity, five-row ordering, fixed query count, and omission of email usernames.
Community API tests cover sent-request listing, owner-only cancellation, and
exclusion of declined requests. Existing tests cover approval and decline.

Frontend checks: `npm.cmd run typecheck` and `npm.cmd run build`.

Browser checks use the synthetic API simulation and isolated browser setup in
[Reader pages](READER_PAGES.md). With those processes running:

```powershell
node scripts/check_community.cjs
```

The script passed guest sign-in prompts, reader links and own-profile links,
page_count, public/private activity, private pending follows, public immediate
follows, approval/decline/cancellation, confirmed unfollow, search empty/error
states, and Community/book-detail layouts at 390px and 768px. Screenshots were
inspected and simulation logs confirmed the real frontend's API traffic.
Fixtures are based on this repository's contracts, not real accounts. Backend
persistence/authorization is tested separately with real Django endpoints and
an isolated database. This does not verify production CORS or deployment state.
