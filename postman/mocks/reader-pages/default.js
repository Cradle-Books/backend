// Local synthetic fixtures based on Cradle views/serializers. No external data.
const http = require('node:http');
const book = id => ({ id, title: `Fixture Book ${id}`, author: 'Fixture Author', cover: null, genre: ['Fantasy'], description: 'A fixture book for local reader-page checks.', page_count: 320, release_date: 2024, average_rating: 4.2 });
const initial = () => ({ profile: { Email: 'reader@example.test', Username: 'Reader', username: 'Reader', Phone: '', Country: 'Nigeria', Address: '', Favourite_genres: ['fantasy'], privacy: 'public', updated_at: new Date().toISOString() }, entries: [1, 2, 3].map((id, i) => ({ id, book: id, status: ['reading', 'finished', 'want'][i], ratings: null, review: null, created_at: `2026-10-0${id}T10:00:00Z`, book_details: book(id) })) });
http.createServer(async (req, res) => {
  const origin = req.headers.origin;
  if (['http://localhost:3104', 'http://127.0.0.1:3104'].includes(origin)) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  const respond = (status, data) => { res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(status === 204 ? '' : JSON.stringify(data)); };
  const path = new URL(req.url, 'http://localhost').pathname.replace(/\/?$/, '/');
  let state = await pm.state.get('reader-pages.state') || initial();
  const save = () => pm.state.set('reader-pages.state', state);
  const body = req.body || {};
  if (path === '/__test/reset/') { state = initial(); await save(); return respond(200, { reset: true }); }
  if (path === '/api/auth/genres/') return respond(200, { genres: [{ key: 'fantasy', name: 'Fantasy' }, { key: 'romance', name: 'Romance' }] });
  if (path === '/api/books/trending/') return respond(200, { results: [4, 5, 6].map(book) });
  if (path.startsWith('/api/books/book/')) return respond(200, { ...book(Number(path.split('/')[4])), number_of_readers: 3, recent_activity: [
    { user: 'Amina', user_id: 12, status: 'reading', status_changed_at: '2026-10-25T10:00:00Z' },
    { user: 'Tunde', user_id: 13, status: 'finished', status_changed_at: '2026-10-24T10:00:00Z' },
    { user: 'Reader', user_id: 1, status: 'want', status_changed_at: '2026-10-23T10:00:00Z' },
  ] });
  if (!req.headers.authorization?.startsWith('Bearer ')) return respond(401, { detail: 'Authentication credentials were not provided.' });
  if (path === '/api/auth/profile/') {
    if (req.method === 'PATCH') {
      if (body.privacy && !['public', 'private'].includes(body.privacy)) return respond(400, { privacy: ['Invalid choice.'] });
      if (body.Favourite_genres?.some(key => !['fantasy', 'romance'].includes(key))) return respond(400, { Favourite_genres: ['Unknown genre.'] });
      Object.assign(state.profile, body, { updated_at: new Date().toISOString() });
      state.profile.username = state.profile.Username || 'Reader'; await save();
    }
    return respond(200, { profile: state.profile, message: 'Profile saved' });
  }
  if (path === '/api/books/profile/') return respond(200, { username: state.profile.username, total_books: state.entries.length, reading: state.entries.filter(e => e.status === 'reading').length, finished: state.entries.filter(e => e.status === 'finished').length, want_to_read: state.entries.filter(e => e.status === 'want').length });
  const readers = [{ id: 12, username: 'Amina', privacy: 'public' }, { id: 13, username: 'Tunde', privacy: 'private' }, { id: 14, username: 'Zara', privacy: 'public' }, { id: 15, username: 'Dayo', privacy: 'private' }, { id: 16, username: 'Emeka', privacy: 'public' }];
  state.social ||= { nextId: 200, relationships: [
    { id: 101, follower: 12, following: 1, state: 'accepted' },
    { id: 102, follower: 14, following: 1, state: 'pending' },
    { id: 103, follower: 15, following: 1, state: 'pending' },
    { id: 104, follower: 1, following: 16, state: 'accepted' },
  ] };
  const relationships = state.social.relationships;
  const connection = (entry, personId) => ({ id: entry.id, user_id: personId, username: readers.find(person => person.id === personId)?.username || 'Reader', state: entry.state });
  if (path === '/api/auth/follows/') return respond(200, {
    followers: relationships.filter(entry => entry.following === 1 && entry.state === 'accepted').map(entry => connection(entry, entry.follower)),
    following: relationships.filter(entry => entry.follower === 1 && entry.state === 'accepted').map(entry => connection(entry, entry.following)),
    outgoing_pending: relationships.filter(entry => entry.follower === 1 && entry.state === 'pending').map(entry => connection(entry, entry.following)),
  });
  if (path === '/api/auth/follow-requests/') return respond(200, { pending: relationships.filter(entry => entry.following === 1 && entry.state === 'pending').map(entry => connection(entry, entry.follower)) });
  if (path === '/api/auth/users/') {
    const username = new URL(req.url, 'http://localhost').searchParams.get('username')?.replace(/^@/, '').toLowerCase();
    if (username === 'error') return respond(503, { message: 'Reader search is temporarily unavailable.' });
    const person = readers.find(reader => reader.username.toLowerCase() === username);
    if (!person) return respond(200, { results: [] });
    const relationship = relationships.find(entry => entry.follower === 1 && entry.following === person.id);
    return respond(200, { results: [{ ...person, follow_status: relationship && relationship.state !== 'declined' ? relationship.state : 'none', follows_you: relationships.some(entry => entry.follower === person.id && entry.following === 1 && entry.state === 'accepted') }] });
  }
  if (path === '/api/auth/follow/' && req.method === 'POST') {
    const person = readers.find(reader => reader.id === body.following);
    if (!person) return respond(400, { following: ['Invalid reader.'] });
    let relationship = relationships.find(entry => entry.follower === 1 && entry.following === person.id);
    if (!relationship) { relationship = { id: state.social.nextId++, follower: 1, following: person.id, state: person.privacy === 'private' ? 'pending' : 'accepted' }; relationships.push(relationship); }
    else if (relationship.state === 'declined') relationship.state = person.privacy === 'private' ? 'pending' : 'accepted';
    await save(); return respond(201, { data: relationship });
  }
  const decision = path.match(/^\/api\/auth\/follow-requests\/(\d+)\/(accept|deny)\/$/);
  if (decision && req.method === 'POST') {
    const relationship = relationships.find(entry => entry.id === Number(decision[1]) && entry.following === 1 && entry.state === 'pending');
    if (!relationship) return respond(404, { message: 'Pending follow request not found.' });
    relationship.state = decision[2] === 'accept' ? 'accepted' : 'declined'; await save(); return respond(200, { data: relationship });
  }
  const cancel = path.match(/^\/api\/auth\/following\/(\d+)\/$/);
  if (cancel && req.method === 'DELETE') {
    const index = relationships.findIndex(entry => entry.id === Number(cancel[1]) && entry.follower === 1);
    if (index === -1) return respond(404, { message: 'Follow relationship not found.' });
    relationships.splice(index, 1); await save(); return respond(204);
  }
  if (path === '/api/books/recommendations/') return respond(200, { results: [] });
  if (path === '/api/books/library/fetch/') return respond(200, { books: state.entries, amount: state.entries.length });
  const update = path.match(/^\/api\/books\/library\/update\/(\d+)\/$/);
  if (update && req.method === 'PATCH') {
    const entry = state.entries.find(e => e.id === Number(update[1]));
    if (!entry) return respond(404, { message: 'Book not found in your library' });
    Object.assign(entry, body); await save(); return respond(200, { data: entry });
  }
  const remove = path.match(/^\/api\/books\/library\/delete\/(\d+)\/$/);
  if (remove && req.method === 'DELETE') { state.entries = state.entries.filter(e => e.id !== Number(remove[1])); await save(); return respond(204); }
  if (path === '/api/auth/change-password/' && req.method === 'POST') {
    if (body.old_password !== 'fixture-password-123') return respond(400, { error: 'Old password is incorrect.' });
    if (body.new_password !== body.confirm_password) return respond(400, { confirm_password: ['New passwords must match.'] });
    return respond(200, { message: 'Password changed successfully' });
  }
  if (path === '/api/auth/logout/') return respond(200, { message: 'Logout successful' });
  respond(501, { message: 'Not modelled by the reader-page simulation.' });
}).listen(process.env.PORT);
