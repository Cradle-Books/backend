// Local browser checks. Requires reader-pages simulation :4906, Next :3104,
// and isolated Chrome CDP :9231. Uses synthetic fixtures only.
const assert = require('node:assert/strict');
const fs = require('node:fs');
let socket;
(async () => {
  await fetch('http://127.0.0.1:4906/cradle/__test/reset');
  const pages = await (await fetch('http://127.0.0.1:9231/json')).json();
  socket = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let id = 0; const pending = new Map();
  socket.onmessage = event => { const data = JSON.parse(event.data); if (data.id) { const item = pending.get(data.id); pending.delete(data.id); data.error ? item.reject(data.error) : item.resolve(data.result); } };
  const call = (method, params = {}) => new Promise((resolve, reject) => { const next = ++id; pending.set(next, { resolve, reject }); socket.send(JSON.stringify({ id: next, method, params })); });
  const evaluate = async expression => { const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; };
  const wait = async (expression, label) => { for (let n = 0; n < 100; n++) { if (await evaluate(expression)) return; await new Promise(resolve => setTimeout(resolve, 150)); } throw new Error(`Timed out: ${label}; ${await evaluate('document.body.innerText.slice(-1300)')}`); };
  const go = async path => { await call('Page.navigate', { url: `http://localhost:3104${path}` }); await wait('document.readyState === "complete"', 'document ready'); };
  const fill = async (selector, value) => { await evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,${JSON.stringify(value)}); el.dispatchEvent(new Event('input',{bubbles:true})); })()`); };
  const select = async (selector, value) => { await evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); el.value=${JSON.stringify(value)}; el.dispatchEvent(new Event('change',{bubbles:true})); })()`); };
  const clickText = async (selector, text) => { await evaluate(`Array.from(document.querySelectorAll(${JSON.stringify(selector)})).find(el=>el.textContent.trim()===${JSON.stringify(text)}).click()`); };
  const screenshot = async name => { const shot = await call('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(`.reader-preview/${name}.png`, Buffer.from(shot.data, 'base64')); };
  const backend = async path => (await fetch(`http://127.0.0.1:4906/cradle${path}`, { headers: { Authorization: 'Bearer fixture-access' } })).json();
  await call('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await go('/discover');
  await evaluate('sessionStorage.setItem("bookapp.access","fixture-access"); sessionStorage.setItem("bookapp.refresh","fixture-refresh"); sessionStorage.setItem("bookapp.username","Reader"); localStorage.removeItem("cradle.appearance")');
  await go('/my-shelf'); await wait('document.querySelectorAll(".shelf-book").length===3', 'three shelf books');
  assert.equal(await evaluate('document.querySelector(".shelf-book-link").getAttribute("href")'), '/books/3');
  await select('select[aria-label="Reading status for Fixture Book 1"]', 'finished');
  await wait('Array.from(document.querySelectorAll(".shelf-tabs button")).some(el=>el.textContent.includes("Finished") && el.textContent.includes("(2)"))', 'status and count updated');
  await select('select[aria-label="Your rating for Fixture Book 1"]', '5');
  await wait('document.body.innerText.includes("Your shelf has been updated.")', 'rating feedback');
  // Wait for the actual write; feedback can also reflect the prior status change.
  for (let n = 0; n < 20; n++) { if ((await backend('/api/books/library/fetch/')).books.find(e => e.id === 1).ratings === 5) break; await new Promise(r => setTimeout(r, 100)); }
  assert.equal((await backend('/api/books/library/fetch/')).books.find(e => e.id === 1).ratings, 5);
  await fill('.shelf-search input', 'no-such-title'); await wait('document.querySelectorAll(".shelf-book").length===0', 'shelf search empty state');
  await fill('.shelf-search input', ''); await wait('document.querySelectorAll(".shelf-book").length===3', 'search cleared');
  await evaluate(`document.querySelector('button[aria-label="Remove Fixture Book 3 from your shelf"]').click()`);
  await clickText('.shelf-remove-confirm button', 'Yes, remove'); await wait('document.querySelectorAll(".shelf-book").length===2', 'confirmed shelf removal');
  await screenshot('shelf-desktop'); console.log('PASS shelf search, status, rating, count, removal, and detail links');
  await go('/profile'); await wait('!!document.querySelector(".profile-visibility") && document.querySelectorAll(".profile-genre-options input").length===2', 'profile ready');
  await evaluate('document.querySelector("input[name=privacy][value=private]").click(); document.querySelectorAll(".profile-genre-options input")[1].click()');
  await evaluate('document.querySelector("#profile-preferences form").requestSubmit()');
  await wait('document.querySelector(".profile-privacy-badge").textContent.includes("Private")', 'private preference saved');
  assert.equal((await backend('/api/auth/profile/')).profile.privacy, 'private');
  assert.ok((await backend('/api/auth/profile/')).profile.Favourite_genres.includes('romance'));
  await fill('input[autocomplete="country-name"]', 'Ghana'); await evaluate('document.querySelector("#profile-information form").requestSubmit()');
  await wait('document.body.innerText.includes("Profile saved.")', 'profile edit saved');
  assert.equal((await backend('/api/auth/profile/')).profile.Country, 'Ghana');
  await go('/profile'); await wait('document.querySelector("input[value=private]")?.checked', 'private preference survives reload');
  await screenshot('profile-desktop'); console.log('PASS profile edits, genre selections, and persisted public/private preference');
  await go('/settings'); await wait('!!document.querySelector("input[name=theme]")', 'settings ready');
  await evaluate('document.querySelector("input[name=theme]").closest("fieldset").querySelectorAll("input")[1].click()');
  await wait('document.documentElement.dataset.theme==="dark"', 'dark appearance');
  await evaluate('document.querySelectorAll("input[name=reading-size]")[2].click()');
  assert.equal(await evaluate('getComputedStyle(document.querySelector(".settings-text-preview")).fontSize'), '17px');
  await go('/settings'); await wait('document.documentElement.dataset.theme==="dark" && document.querySelectorAll("input[name=reading-size]")[2]?.checked', 'appearance persists');
  assert.equal(await evaluate('Array.from(document.querySelectorAll(".settings-unavailable input")).every(el=>el.disabled)'), true);
  const passwordFields = '#password input';
  await fill(`${passwordFields}:nth-of-type(1)`, 'wrong-password');
  await fill('#password label:nth-of-type(2) input', 'changed-password-123');
  await fill('#password label:nth-of-type(3) input', 'changed-password-123');
  await evaluate('document.querySelector("#password form").requestSubmit()');
  await wait('document.querySelector("#password").innerText.includes("Old password is incorrect.")', 'password failure shown');
  await fill('#password label:nth-of-type(1) input', 'fixture-password-123'); await evaluate('document.querySelector("#password form").requestSubmit()');
  await wait('document.querySelector("#password").innerText.includes("Password updated.")', 'password success');
  await screenshot('settings-desktop'); console.log('PASS appearance persistence, unavailable notifications, and password failure/success');
  for (const width of [390, 768]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width === 390 });
    for (const route of ['/my-shelf', '/profile', '/settings']) {
      await go(route); await wait('!!document.querySelector(".reader-page")', `${route} loaded`);
      await new Promise(resolve => setTimeout(resolve, 400));
      assert.ok(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), `${route} overflows at ${width}`);
      if (width === 390) await screenshot(`${route.slice(1)}-mobile`);
    }
    console.log(`PASS three pages fit ${width}px viewport`);
  }
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => socket?.close());
