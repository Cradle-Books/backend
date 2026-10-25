// Search response fields follow https://openlibrary.org/dev/docs/api/search.
// Synthetic titles isolate these checks from production data.
const http = require('node:http');
http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname !== '/search.json') { res.writeHead(501); res.end(); return; }
  const query = url.searchParams.get('q') || '';
  res.setHeader('Content-Type', 'application/json');
  if (query.includes('slow')) { const timer = setTimeout(() => res.end('{"docs":[]}'), 12000); res.on('close', () => clearTimeout(timer)); return; }
  if (query.includes('unavailable')) { res.writeHead(503); res.end('{"error":"Unavailable"}'); return; }
  if (query.includes('malformed')) { res.end('<html>upstream error</html>'); return; }
  const page = Number(url.searchParams.get('page') || 1);
  const limit = Number(url.searchParams.get('limit') || 12);
  res.end(JSON.stringify({ start: (page - 1) * limit, numFound: 100, docs: Array.from({ length: limit }, (_, i) => ({
    key: `/works/SIM${(page - 1) * limit + i}W`, title: `Search fixture ${(page - 1) * limit + i}`, author_name: ['Fixture Author'],
    cover_i: 123, first_publish_year: 2020, subject: ['Fiction'], ratings_average: 4.2, edition_count: 1,
  })) }));
}).listen(process.env.PORT);
