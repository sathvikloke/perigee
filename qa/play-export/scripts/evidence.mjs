// Evidence card: save, reload, export a real card; storage failure; URLs.
import { chromium } from "playwright-core";
import { readFileSync } from "node:fs";
const BASE = process.env.BASE ?? "http://localhost:5198/";
const OUT = process.env.OUT ?? ".";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const log = (...a) => console.log(...a);

const NOTES = {
  claim: "Barnard's Star sits north of the guide line in C; the field stars stay put.",
  observations: "A (25 Aug 2025) and C (19 Aug 2026): field stars land on the same pixels; the bright star's glow is above the dashed line in C.",
  uncertainty: "A and C are at slightly different wavelengths and flagged near the target, so I can't measure how far it moved.",
};

async function ready(page, route) {
  await page.goto(BASE + route);
  await page.waitForSelector(".notebook textarea", { timeout: 60000 });
  await page.waitForSelector(".sequence .play-toggle", { timeout: 60000 });
}
const notebook = (page) =>
  page.evaluate(() => ({
    fields: [...document.querySelectorAll(".notebook textarea")].map((t) => t.value),
    status: document.querySelector(".notebook-actions [role=status]").textContent,
    attached: document.querySelector(".notebook .attached")?.textContent.replace(/\s+/g, " ").trim(),
    search: location.search,
  }));
async function fill(page) {
  const ta = page.locator(".notebook textarea");
  await ta.nth(0).fill(NOTES.claim);
  await ta.nth(1).fill(NOTES.observations);
  await ta.nth(2).fill(NOTES.uncertainty);
}
async function exportTo(page, path) {
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click(".notebook button.primary")]);
  await dl.saveAs(path);
  return { suggested: dl.suggestedFilename(), path };
}

// ---- 1. Save, reload, export a real card (Barnard's Star, live API)
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  await ready(page, "?preset=barnards_star");
  await fill(page);
  // Attach one extra (non-case) frame from the full sequence.
  await page.locator(".sequence").scrollIntoViewIfNeeded();
  await page.click('.sequence button[aria-label="Later frame"]');
  await page.click('.sequence button[aria-label="Later frame"]');
  await page.click(".sequence .sequence-side > button");
  await page.waitForTimeout(700);
  const saved = await notebook(page);
  log("after edit:", saved.status, "|", saved.attached);
  const raw = await page.evaluate(() => localStorage.getItem("perigee.evidence.v1"));
  const store = JSON.parse(raw);
  log("stored cards:", store.cards.length, "contexts:", JSON.stringify(store.contexts));
  await page.reload();
  await page.waitForSelector(".notebook textarea", { timeout: 60000 });
  await page.waitForTimeout(300);
  const restored = await notebook(page);
  log("after reload:", restored.status, "| fields equal:", JSON.stringify(restored.fields) === JSON.stringify(Object.values(NOTES)), "|", restored.attached);
  const ex = await exportTo(page, `${OUT}/barnards_star-evidence-card.json`);
  log("exported:", ex.suggested);
  log("status after export:", (await notebook(page)).status, "| URL:", (await notebook(page)).search);
  await page.locator(".notebook").screenshot({ path: `${OUT}/notebook-restored-1280.jpg`, type: "jpeg", quality: 80 });
  await ctx.close();
}

// ---- 2. Storage refuses every write (quota): notes survive in memory
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  await ctx.addInitScript(() => {
    const orig = Storage.prototype.setItem;
    window.__setItemCalls = 0;
    Storage.prototype.setItem = function (k, v) {
      if (String(k).startsWith("perigee")) {
        window.__setItemCalls++;
        throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
      }
      return orig.call(this, k, v);
    };
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await ready(page, "?preset=barnards_star");
  await fill(page);
  await page.waitForTimeout(700);
  const a = await notebook(page);
  log("quota: status:", a.status, "| setItem attempts:", await page.evaluate(() => window.__setItemCalls));
  // Leave the target in-app and come back.
  await page.click(".brand");
  await page.waitForSelector("#my-evidence", { timeout: 30000 });
  const home = await page.evaluate(() => document.querySelector("#my-evidence").textContent.replace(/\s+/g, " ").trim());
  log("quota: home list:", home.slice(0, 160));
  await page.goBack();
  await page.waitForSelector(".notebook textarea", { timeout: 60000 });
  await page.waitForTimeout(300);
  const b = await notebook(page);
  log("quota: after leave/return:", b.status, "| notes kept:", JSON.stringify(b.fields) === JSON.stringify(Object.values(NOTES)));
  await page.locator(".notebook .notebook-actions").scrollIntoViewIfNeeded();
  await page.locator(".notebook").screenshot({ path: `${OUT}/storage-failure-notebook-1280.jpg`, type: "jpeg", quality: 80 });
  const ex = await exportTo(page, `${OUT}/storage-failure-export.json`);
  const card = JSON.parse(readFileSync(ex.path, "utf8"));
  log("quota: export still works:", ex.suggested, "| claim kept:", card.claim === NOTES.claim, "| frames:", card.frames.length);
  log("quota: page errors:", errors.length ? errors : "none");
  await ctx.close();
}

// ---- 3. localStorage getter throws (storage blocked entirely)
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("denied", "SecurityError");
      },
    });
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await ready(page, "?preset=barnards_star");
  await fill(page);
  await page.waitForTimeout(700);
  const a = await notebook(page);
  log("blocked: status:", a.status, "| notes on screen:", a.fields[0] === NOTES.claim, "| page errors:", errors.length ? errors : "none");
  await ctx.close();
}

// ---- 4. Blink and Play are mutually exclusive (wise_0855 has the blink tool)
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await ready(page, "?preset=wise_0855");
  const blink = page.locator(".pair-picker button");
  await blink.click();
  await page.click(".sequence .play-toggle");
  await page.waitForTimeout(200);
  const s1 = await page.evaluate(() => [document.querySelector(".pair-picker button").getAttribute("aria-pressed"), document.querySelector(".play-toggle").getAttribute("aria-pressed")]);
  await blink.click();
  await page.waitForTimeout(200);
  const s2 = await page.evaluate(() => [document.querySelector(".pair-picker button").getAttribute("aria-pressed"), document.querySelector(".play-toggle").getAttribute("aria-pressed")]);
  await page.click(".sequence .play-toggle");
  await page.selectOption(".pair-picker select >> nth=0", { index: 1 });
  await page.waitForTimeout(200);
  const s3 = await page.evaluate(() => document.querySelector(".play-toggle").getAttribute("aria-pressed"));
  log("wise_0855 [blink,play] after Blink→Play:", s1, "after Play→Blink:", s2, "play after pair change:", s3);
  await ctx.close();
}
await browser.close();
