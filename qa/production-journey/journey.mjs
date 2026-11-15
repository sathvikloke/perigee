import { chromium } from 'playwright-core';
import fs from 'node:fs';
// Usage: node journey.mjs <base-origin> <out-dir>
// e.g. node journey.mjs https://perigee-liard.vercel.app qa/production/2026-11-15
// Runs logged out in fresh browser contexts (no stored evidence), headless system Chrome.
const BASE = (process.argv[2] || '').replace(/\/$/, ''); const OUT = process.argv[3];
if (!/^https?:\/\/[^/]+$/.test(BASE) || !OUT) { console.error('usage: node journey.mjs <origin> <out-dir>'); process.exit(2); }
if (/^https?:\/\/perigee\.vercel\.app\.?(:\d+)?$/i.test(BASE)) { console.error('REFUSED: perigee.vercel.app is an unrelated app'); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });
const log = []; const L = (k, v) => { log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 400)); };
const CLAIM = "A and B are a fair pair (five months apart, 2.323 and 2.322 µm, no flags at the target), and Epsilon Indi B looks the same in both. A and C look different because C shows 4.94 µm light, where Epsilon Indi B stands out and most stars fade.";
const NOTICE = "In A a bright dot sits just below and right of the marker. With flagged pixels shown it is marked as a problem flag, so it is a bad pixel, not a change. In C most field stars fade while Epsilon Indi B stays bright.";
const UNCERTAIN = "No brightness was measured and each plate is stretched for display, so I cannot say whether Epsilon Indi B got brighter or fainter.";
const b = await chromium.launch({ executablePath: process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const bench = (p) => p.locator('div, section').filter({ has: p.getByRole('button', { name: /Blink|Pause blink/ }) }).filter({ hasText: 'Same sky grid' }).last();
const shot = async (p, name, opts = {}) => { await p.waitForTimeout(400); await p.screenshot({ path: `${OUT}/${name}`, type: 'jpeg', quality: 85, ...opts }); L('shot', { name }); };
const imgsReady = async (p) => { await p.waitForFunction(() => [...document.querySelectorAll('img')].filter(i => i.offsetParent).every(i => i.complete && i.naturalWidth > 0), null, { timeout: 30000 }).catch(() => {}); };
const overflow = (p) => p.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth }));
const text = (p) => p.evaluate(() => document.body.innerText);

// ---------------- desktop
const D = await b.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2, acceptDownloads: true });
const p = await D.newPage();
const api = []; p.on('request', r => { const u = r.url(); if (/\/api\/v1\/(search|frame)/.test(u)) api.push(u); });
const errs = []; p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
L('storage_clean', { origin: BASE, note: 'fresh Playwright context; no prior localStorage' });

const t0 = Date.now(); const resp = await p.goto(BASE + '/'); await p.waitForLoadState('networkidle').catch(() => {});
L('first_visit', { status: resp?.status(), url: p.url(), ms_to_networkidle: Date.now() - t0, title: await p.title(), presets: (await p.locator('button', { hasText: /Guided investigation|Free exploration/ }).count()) || (await p.locator('main button').count()) });
const h = await p.request.get(BASE + '/api/v1/health'); let hb = {}; try { hb = await h.json(); } catch {}
L('health', { status: h.status(), ctype: h.headers()['content-type'], api_status: hb.status, token_signing: hb.capabilities?.token_signing, processor: hb.capabilities?.frame_processor });
await p.keyboard.press('Tab');
L('keyboard_first_tab', { focused: await p.evaluate(() => document.activeElement?.textContent?.trim().slice(0, 40)), outline: await p.evaluate(() => getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).outlineWidth) });
await shot(p, 'd01-home-1280.jpg');

await p.goto(BASE + '/?preset=epsilon_indi_b'); await imgsReady(p);
L('eps_AB', { url: p.url(), focus: await p.evaluate(() => document.activeElement?.tagName + ':' + document.activeElement?.textContent?.slice(0, 40)),
  note: (await text(p)).match(/Different dates, nearly the same wavelength[^\n]*\n[^\n]+/)?.[0], dates: (await text(p)).match(/\d{1,2} \w{3} 2026/g)?.slice(0, 2) });
await shot(p, 'd02-eps-AB-1280.jpg');
await bench(p).screenshot({ path: `${OUT}/d02b-eps-AB-bench-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd02b-eps-AB-bench-1280.jpg' });

await p.getByRole('button', { name: /Blink pair/ }).click(); await p.waitForTimeout(2600);
L('blink', { pressed: await p.getByRole('button', { name: /Blink|Pause|Stop/ }).first().getAttribute('aria-pressed'), label: await p.getByRole('button', { name: /Blink|Pause|Stop/ }).first().textContent() });
await p.getByRole('button', { name: /Blink|Pause|Stop/ }).first().click(); await p.waitForTimeout(300);

await p.getByRole('button', { name: /A \+ C/ }).focus(); await p.keyboard.press('Enter'); await imgsReady(p); await p.waitForTimeout(500);
L('keyboard_AC', { pressed: await p.getByRole('button', { name: /A \+ C/ }).getAttribute('aria-pressed') });
const tAC = await text(p);
L('eps_AC', { wavelengths: tAC.match(/\d\.\d{4} µm/g)?.slice(0, 3), note: tAC.match(/Same moment[^\n]*\n[^\n]+/)?.[0], stretch: tAC.match(/[^\n]*(stretch|comparable)[^\n]*/gi)?.slice(0, 4) });
await shot(p, 'd03-eps-AC-1280.jpg');
await bench(p).scrollIntoViewIfNeeded(); await bench(p).screenshot({ path: `${OUT}/d03b-eps-AC-bench-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd03b-eps-AC-bench-1280.jpg' });

await p.getByRole('button', { name: /A \+ B/ }).click(); await imgsReady(p);
await p.evaluate(() => window.scrollTo(0, 0));
const flagBox = p.getByLabel('Show flagged pixels').first(); await flagBox.check(); await p.waitForTimeout(600);
const tF = await text(p);
L('flags', { checked: await flagBox.isChecked(), legend: tF.match(/[^\n]*(Hatched|legend|colour key|color key|adverse)[^\n]*/gi)?.slice(0, 4) });
await bench(p).screenshot({ path: `${OUT}/d04-eps-AB-flags-bench-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd04-eps-AB-flags-bench-1280.jpg' });
const fsum = p.locator('summary', { hasText: 'What does “flag screen passed” mean?' });
await fsum.click(); await p.waitForTimeout(300);
L('flag_meaning', { text: (await fsum.locator('xpath=..').innerText()).slice(0, 600) });
await fsum.locator('xpath=..').screenshot({ path: `${OUT}/d05-flag-screen-meaning-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd05-flag-screen-meaning-1280.jpg' });
const qsum = p.locator('summary', { hasText: 'Quality details' }).first();
if (await qsum.count()) { await qsum.click(); await p.waitForTimeout(300); L('quality_details', { text: (await qsum.locator('xpath=..').innerText()).slice(0, 700) }); }

await p.getByLabel('What’s your claim?').fill(CLAIM);
await p.getByLabel('What did you notice?').fill(NOTICE);
await p.getByLabel('What remains uncertain?').fill(UNCERTAIN);
await p.waitForTimeout(800);
const nb = p.locator('text=Evidence notebook').first().locator('xpath=ancestor::*[self::section or self::aside][1]');
await nb.scrollIntoViewIfNeeded(); await nb.screenshot({ path: `${OUT}/d06-notebook-filled-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd06-notebook-filled-1280.jpg' });
L('notebook', { counter: (await nb.innerText()).match(/\d+ \/ 280/)?.[0], saved: (await nb.innerText()).match(/[^\n]*(Saved|saved|device)[^\n]*/)?.[0] });

const gsum = p.locator('summary', { hasText: 'Check your claim against the case guide' });
await gsum.click(); await p.waitForTimeout(400);
const g = gsum.locator('xpath=..'); await g.scrollIntoViewIfNeeded();
L('claim_guide', { text: (await g.innerText()).slice(0, 900) });
await g.screenshot({ path: `${OUT}/d07-claim-guide-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd07-claim-guide-1280.jpg' });

const [dl] = await Promise.all([p.waitForEvent('download'), p.getByRole('button', { name: /Export evidence card/ }).click()]);
const exportPath = `${OUT}/evidence-card-fair_comparison.json`; await dl.saveAs(exportPath);
L('export', { suggested: dl.suggestedFilename(), status: (await text(p)).match(/[^\n]*(downloaded|Exported|export)[^\n]*/i)?.[0] });

await p.evaluate(() => { window.__printed = 0; window.print = () => { window.__printed++; }; });
await p.getByRole('button', { name: /Print \/ save PDF/ }).click(); await p.waitForTimeout(300);
L('print_button', { window_print_calls: await p.evaluate(() => window.__printed) });
await p.emulateMedia({ media: 'print' });
await p.pdf({ path: `${OUT}/evidence-card-fair_comparison-print.pdf`, format: 'Letter', printBackground: true, margin: { top: '0.5in', bottom: '0.5in', left: '0.5in', right: '0.5in' } });
await p.emulateMedia({ media: 'screen' }); L('pdf', { path: 'evidence-card-fair_comparison-print.pdf' });
L('irsa_calls_during_case', { count: api.length });

// My evidence -> Reopen
await p.getByRole('link', { name: 'Perigee home' }).click(); await p.waitForTimeout(1500);
const saved = p.locator('section, div').filter({ has: p.locator('#saved-h') }).filter({ has: p.getByRole('link', { name: /^Reopen/ }) }).last(); await saved.scrollIntoViewIfNeeded();
L('my_evidence', { text: (await saved.innerText()).slice(0, 400) });
await saved.screenshot({ path: `${OUT}/d08-my-evidence-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd08-my-evidence-1280.jpg' });
await p.getByRole('link', { name: /^Reopen/ }).first().click(); await imgsReady(p); await p.waitForTimeout(800);
L('reopen', { url: p.url(), focus: await p.evaluate(() => document.activeElement?.tagName + ':' + document.activeElement?.textContent?.slice(0, 40)),
  claim_restored: (await p.getByLabel('What’s your claim?').inputValue()) === CLAIM, notice_restored: (await p.getByLabel('What did you notice?').inputValue()) === NOTICE,
  uncertain_restored: (await p.getByLabel('What remains uncertain?').inputValue()) === UNCERTAIN });
await p.reload(); await imgsReady(p); await p.waitForTimeout(800);
L('reload', { claim_restored: (await p.getByLabel('What’s your claim?').inputValue()) === CLAIM });

// Barnard backup
await p.goto(BASE + '/?preset=barnards_star'); await imgsReady(p); await p.waitForTimeout(600);
const tB = await text(p);
L('barnard', { h1: await p.locator('h1').textContent(), pair: tB.match(/\d{1,2} \w{3} 202\d/g)?.slice(0, 2), quality: tB.match(/Flagged near target|Flag screen passed/g)?.slice(0, 2) });
await shot(p, 'd09-barnard-AC-guide-flags-1280.jpg');
await bench(p).scrollIntoViewIfNeeded(); await bench(p).screenshot({ path: `${OUT}/d09b-barnard-AC-bench-1280.jpg`, type: 'jpeg', quality: 85 }); L('shot', { name: 'd09b-barnard-AC-bench-1280.jpg' });
L('irsa_calls_after_presets', { count: api.length });

// Invalid input is rejected client-side, with no request
{ const pv = await D.newPage(); let sent = 0; pv.on('request', r => { if (r.url().includes('/api/v1/search')) sent++; });
  await pv.goto(BASE + '/?view=query'); await pv.waitForTimeout(800);
  await pv.getByLabel(/Right ascension/).fill('400'); await pv.getByLabel(/Declination/).fill('12abc');
  await pv.getByRole('button', { name: /Search the archive/ }).click(); await pv.waitForTimeout(800);
  L('validation', { requests_sent: sent, messages: (await pv.evaluate(() => document.body.innerText)).match(/[^\n]*(must|between|number|Enter)[^\n]*/gi)?.slice(0, 3) });
  await shot(pv, 'd12-validation-1280.jpg'); await pv.close(); }

// Coordinate link (live IRSA)
await p.getByRole('link', { name: /Search coordinates/ }).click(); await p.waitForTimeout(800);
await p.getByRole('button', { name: /Use Epsilon Indi A, J2000 catalog position/ }).click().catch(async () => { await p.getByText(/Use Epsilon Indi A, J2000 catalog position/).click(); });
await p.getByRole('button', { name: /Search the archive/ }).click();
await p.waitForFunction(() => /\d+ ready · 0 processing · 0 waiting/.test(document.body.innerText) || /search failed|could not/i.test(document.body.innerText), null, { timeout: 120000 }).catch(() => {});
const tQ = await text(p);
L('coordinate_search', { url: p.url(), found: tQ.match(/\d+ observations found[^.]*/)?.[0], summary: tQ.match(/\d+ ready · \d+ processing · \d+ waiting · \d+ failed/)?.[0], moved: tQ.match(/[^\n]*moved about 2′[^\n]*/)?.[0] });
await p.evaluate(() => window.scrollTo(0, 0)); await shot(p, 'd10-coordinate-search-1280.jpg');
const retry = p.getByRole('button', { name: /^Retry \d+ failed/ });
if (await retry.count()) { await retry.first().click(); await p.waitForTimeout(20000);
  L('retry_failed', { after: (await text(p)).match(/\d+ ready · \d+ processing · \d+ waiting · \d+ failed/)?.[0] }); }
else L('retry_failed', { note: 'no failed frames to retry in this run' });
// Non-preset deep link (coordinate link shared as URL)
{ const pd = await D.newPage(); await pd.goto(BASE + '/?view=query&ra=83.82&dec=-5.39&fov=6'); await pd.waitForTimeout(800);
  L('coordinate_link', { ra: await pd.getByLabel(/Right ascension/).inputValue(), dec: await pd.getByLabel(/Declination/).inputValue() }); await pd.close(); }

// Simulated archive failure (fallback slide)
const pf = await D.newPage();
await pf.route('**/api/v1/search', r => r.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ schema_version: 1, request_id: 'rehearsal-sim-502', error: { code: 'UPSTREAM_UNAVAILABLE', message: 'The NASA/IPAC archive is unavailable right now.', retryable: true } }) }));
await pf.goto(BASE + '/?view=query&ra=330.84&dec=-56.786&fov=6'); await pf.waitForTimeout(800);
await pf.getByRole('button', { name: /Search the archive/ }).click(); await pf.waitForTimeout(1500);
L('simulated_failure', { text: (await text(pf)).match(/[^\n]*(not a result about the sky|failed|unavailable)[^\n]*/gi)?.slice(0, 3) });
await shot(pf, 'd11-simulated-archive-failure-1280.jpg');
L('console_errors_desktop', { count: errs.length, first: errs.slice(0, 3) });

// ---------------- phone
for (const [w, h] of [[390, 844], [320, 700]]) {
  const P = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  const q = await P.newPage();
  await q.goto(BASE + '/?preset=epsilon_indi_b'); await imgsReady(q);
  L(`phone${w}_eps_AB`, await overflow(q)); await shot(q, `p01-eps-AB-${w}.jpg`);
  await q.getByRole('button', { name: /A \+ C/ }).tap(); await imgsReady(q); L(`phone${w}_eps_AC`, await overflow(q)); await shot(q, `p02-eps-AC-${w}.jpg`);
  await q.getByRole('button', { name: /A \+ B/ }).tap(); await imgsReady(q);
  await q.getByLabel('Show flagged pixels').first().check(); await q.waitForTimeout(500); await shot(q, `p03-eps-AB-flags-${w}.jpg`);
  await q.getByLabel('What’s your claim?').fill(CLAIM); await q.getByLabel('What’s your claim?').scrollIntoViewIfNeeded(); L(`phone${w}_notebook`, await overflow(q)); await shot(q, `p04-notebook-${w}.jpg`);
  await q.goto(BASE + '/?preset=barnards_star'); await imgsReady(q); L(`phone${w}_barnard`, await overflow(q)); await shot(q, `p05-barnard-${w}.jpg`);
  await q.goto(BASE + '/'); await q.waitForTimeout(1200); const s = q.locator('#saved-h'); await s.scrollIntoViewIfNeeded(); L(`phone${w}_my_evidence`, await overflow(q)); await shot(q, `p06-my-evidence-${w}.jpg`);
  await P.close();
}
fs.writeFileSync(`${OUT}/journey-log.json`, JSON.stringify(log, null, 1));
await b.close();
