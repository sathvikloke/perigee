// Focused browser checks for contract behaviors not covered by the journey:
// expired frame token (simulated 410 TOKEN_EXPIRED) keeps notes and offers a
// re-run; a newer coordinate search replaces an older in-flight one (stale
// response never shown); a shared query URL carries no notes.
// Usage: node contract-checks.mjs <origin> <out-dir>
import { chromium } from 'playwright-core';
import fs from 'node:fs';
const BASE = (process.argv[2] || '').replace(/\/$/, ''); const OUT = process.argv[3];
if (!/^https?:\/\/[^/]+$/.test(BASE) || !OUT || /perigee\.vercel\.app\.?(:\d+)?$/i.test(BASE)) { console.error('usage: node contract-checks.mjs <origin> <out-dir>'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });
const log = []; const L = (k, v) => { log.push({ check: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 500)); };
const b = await chromium.launch({ executablePath: process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
const text = (p) => p.evaluate(() => document.body.innerText);
const NOTE = 'Contract check note: keep me.';

// 1. Expired token: every /frame answers 410 TOKEN_EXPIRED (simulated).
{ const p = await ctx.newPage();
  await p.route('**/api/v1/frame', r => r.fulfill({ status: 410, contentType: 'application/json', body: JSON.stringify({ schema_version: 1, request_id: 'contract-sim-410', error: { code: 'TOKEN_EXPIRED', message: 'The frame token has expired.', retryable: false, details: { hint: 'refresh' } } }) }));
  await p.goto(BASE + '/?view=query&ra=330.84&dec=-56.786&fov=6'); await p.waitForTimeout(800);
  const lim = p.getByLabel(/Maximum results/); await lim.fill('3');
  await p.getByLabel('What’s your claim?').fill(NOTE);
  await p.getByRole('button', { name: /Search the archive/ }).click();
  await p.waitForFunction(() => /has expired/i.test(document.body.innerText), null, { timeout: 60000 }).catch(() => {});
  const t = await text(p);
  L('expired_token', { banner: t.match(/[^\n]*has expired[^\n]*/i)?.[0], rerun_button: await p.getByRole('button', { name: /Run the search again/ }).count(), notes_kept: (await p.getByLabel('What’s your claim?').inputValue()) === NOTE, summary: t.match(/\d+ ready · \d+ processing · \d+ waiting · \d+ failed/)?.[0] });
  await p.screenshot({ path: `${OUT}/c01-expired-token-simulated.jpg`, type: 'jpeg', quality: 80 });
  await p.unroute('**/api/v1/frame');
  let reruns = 0; p.on('request', r => { if (r.url().endsWith('/api/v1/search')) reruns++; });
  await p.getByRole('button', { name: /Run the search again/ }).click();
  // Wait for at least one READY frame of the new search (the old summary reads "0 ready ... 3 failed").
  await p.waitForFunction(() => /[1-9]\d* ready · 0 processing · 0 waiting/.test(document.body.innerText), null, { timeout: 90000 }).catch(() => {});
  L('expired_token_rerun_requests', { searches_sent_after_click: reruns });
  L('expired_token_rerun', { summary: (await text(p)).match(/\d+ ready · \d+ processing · \d+ waiting · \d+ failed/)?.[0], notes_kept: (await p.getByLabel('What’s your claim?').inputValue()) === NOTE });
  await p.close(); }

// 2. Stale response: start search A, change to B before A returns; only B may show.
{ const p = await ctx.newPage(); const seen = [];
  p.on('response', async r => { if (r.url().endsWith('/api/v1/search')) { try { const j = await r.json(); seen.push(`${j.query?.ra_deg},${j.query?.dec_deg}`); } catch {} } });
  await p.route('**/api/v1/search', async r => { const body = JSON.parse(r.request().postData() || '{}'); if (body.ra_deg === 330.84) await new Promise(res => setTimeout(res, 4000)); await r.continue(); });
  await p.goto(BASE + '/?view=query'); await p.waitForTimeout(800);
  await p.getByLabel(/Right ascension/).fill('330.84'); await p.getByLabel(/Declination/).fill('-56.786'); await p.getByLabel(/Maximum results/).fill('2');
  await p.getByRole('button', { name: /Search the archive/ }).click(); await p.waitForTimeout(500);
  await p.getByLabel(/Right ascension/).fill('83.822'); await p.getByLabel(/Declination/).fill('-5.391');
  await p.getByRole('button', { name: /Search the archive/ }).click();
  await p.waitForTimeout(9000);
  const t = await text(p);
  L('stale_response', { responses_received: seen, shown_query: t.match(/RA [\d.]+°, Dec -?[\d.]+°, \d+′ field/)?.[0], url: p.url(), shows_old: /RA 330\.84°/.test(t) && !/RA 83\.822°/.test(t) });
  await p.screenshot({ path: `${OUT}/c02-stale-response.jpg`, type: 'jpeg', quality: 80 });
  // 3. Shared URL carries coordinates only, never notes.
  await p.getByLabel('What’s your claim?').fill(NOTE).catch(() => {});
  await p.waitForTimeout(500);
  L('share_url', { url: p.url(), contains_note: decodeURIComponent(p.url()).includes('keep me') });
  await p.close(); }
fs.writeFileSync(`${OUT}/contract-checks-log.json`, JSON.stringify(log, null, 1));
await b.close();
