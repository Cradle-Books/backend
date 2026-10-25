# Search latency and upstream failures

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
