# Search latency and upstream failures

## What made search slow

The browser was waiting for more work than the search screen needed. Previously,
the backend enriched incomplete cached books through Google Books. If the page
still needed external matches, it called Open Library search, then visited each
work record and often Google Books before returning the list.

For a twelve-book external page, that could mean one search request plus twelve
work requests and twelve Google lookups. Google lookups could also retry a 503.
Most of the external-book enrichment happened sequentially: the next lookup
waited for the previous lookup to finish.

For illustration, if the initial search took 1 second and each of 12 work calls
took 2 seconds, those calls alone would take about 25 seconds. This is an example,
not a measured benchmark; Google calls and database work would add more time.
The frontend only waits 20 seconds, so it could cancel while the backend was
still working. A 10-second timeout on each upstream call never meant a
10-second timeout on the whole search.

## Why the change helps

| Path | Before | Now |
| --- | --- | --- |
| Full cached page | Could wait for Google metadata enrichment | Returns stored list fields with no external calls |
| External results needed | Search plus repeated work and Google lookups | One Open Library search call |
| Full description needed | Fetched for search results before the user chose a book | Fetched through book details when the user opens a book |
| Upstream failure with cached matches | Discarded the partial cached page | Returns available cached matches |

This is **lazy loading**: defer expensive information until someone needs it.
It also removes an **N+1 request pattern**, where one list request triggers more
requests for each of N items. We reduced the work on the **critical path**, meaning
the operations that must finish before the user can see search results.

We did not make Open Library itself faster or remove all external requests.
We stopped waiting for unnecessary detail requests on the search screen.
Descriptions may therefore be empty in search results, and ratings may be null
when upstream search does not provide them. Previously saved metadata is retained.
The existing detail endpoint still has its original upstream latency.

## The two timeout boundaries

The frontend-to-Cradle request and Cradle-to-Open-Library request are separate:

```text
Browser -- waits up to 20 seconds --> Cradle
                                      |
                                      +-- connect: 3s, read: 10s --> Open Library
```

A browser status of `canceled` indicates that the client stopped waiting; it
does not by itself identify the reason. Navigation or an explicit abort can also
cancel requests. The backend `ReadTimeout` identifies a different boundary:
Cradle waited too long to read from Open Library. Compare browser timing and
backend logs to connect the two observations.

The read timeout measures waiting for data on the socket, not a hard deadline
for the complete response. Cold starts, connection setup, and other work also
contribute to the browser's elapsed time. These settings reduce the likelihood
of cancellation but cannot guarantee every request finishes within 20 seconds.
Increasing the browser timeout alone would let users wait longer without removing
the extra work that caused this problem.

## Current API behavior

`GET /api/books/search/?q=title&page=1&page_size=12` keeps its existing response
shape. Cached results include any description and rating already stored. Search
also matches cached author names.

Search makes at most one Open Library request per page, with a 3-second connect
timeout and a 10-second read timeout. These are socket timeouts, not a guaranteed
whole-request deadline. It explicitly requests the list fields documented at
https://openlibrary.org/dev/docs/api/search. It no longer fetches each work or
Google Books metadata before returning the list. Open a book's existing detail
endpoint to fetch missing full metadata; that endpoint's latency is unchanged.

On an upstream timeout, HTTP error, or invalid response, cached page results are
returned with `source: db` when available. Without cached results, the endpoint
returns 503 with a retryable message. The browser currently aborts requests after
20 seconds; cold starts and other infrastructure delays can still exceed that.

## Local HTTP simulation

The mock uses synthetic fixtures with the documented Open Library search shape.
No published provider mock was used. The mock answers 501 for unrelated routes;
only the upstream search service is simulated, not Cradle or its database.

In one PowerShell terminal:

```powershell
postman simulation run postman/simulations/search.sim.yaml --port 4905 --output ndjson --no-history
```

In another, from `backend`:

```powershell
$env:SEARCH_SIMULATION_URL = 'http://127.0.0.1:4905/open-library'
$env:DATABASE_URL = ''
../.venv/Scripts/python.exe manage.py test Azaniah.books
```

The tests use a separate Django test database. Simulation tests are skipped when
`SEARCH_SIMULATION_URL` is absent. They cover twelve results, page two, a 503
with cached fallback, invalid JSON, and a real HTTP read timeout. The `slow`
fixture waits 12 seconds, exceeding the backend's 10-second read timeout.
`OPEN_LIBRARY_BASE_URL` defaults to the real service; use its override only for
local simulation. Stop the simulation with Ctrl+C when finished.

## What the verification establishes

The local books suite passed 16 tests with the simulation enabled. After the
final logging adjustment, the five simulation tests passed again. A simulated
12-second upstream delay caused a controlled 503 after approximately 10 seconds,
before the frontend timeout. Simulation logs confirmed real HTTP requests from
Cradle to the stand-in rather than only a patched Python HTTP client.

These checks establish behavior against controlled fixtures, not live provider
uptime or a production speed benchmark. The user subsequently reported much
faster search; no precise before/after production timings were recorded.

To investigate similar issues, inspect the request's duration in browser Network,
count external calls made per page, and time the database query, upstream search,
and optional enrichment separately. Optimize the work users must wait for before
increasing timeout values. Measure repeated cached searches separately from first
searches, because those paths do different amounts of work.
