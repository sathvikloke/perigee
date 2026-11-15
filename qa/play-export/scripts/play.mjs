// Play over the series: cadence, labels, announcements, stop rules, screenshots.
import { chromium } from "playwright-core";
const BASE = process.env.BASE ?? "http://localhost:5198/";
const OUT = process.env.OUT ?? ".";
const ROUTE = process.env.ROUTE ?? "?preset=barnards_star";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const log = (...a) => console.log(...a);

async function open(width, height, reduced = false) {
  const ctx = await browser.newContext({ viewport: { width, height }, reducedMotion: reduced ? "reduce" : "no-preference" });
  const page = await ctx.newPage();
  await page.goto(BASE + ROUTE);
  await page.waitForSelector(".sequence .play-toggle", { timeout: 60000 });
  await page.waitForFunction(() => document.querySelectorAll(".sequence .plate img").length > 0, null, { timeout: 60000 });
  // Count live-region text changes in the sequence viewer.
  await page.evaluate(() => {
    const live = document.querySelector('.sequence [aria-live="polite"]');
    window.__live = [];
    new MutationObserver(() => window.__live.push(live.textContent)).observe(live, { childList: true, characterData: true, subtree: true });
  });
  return { ctx, page };
}

const state = (page) =>
  page.evaluate(() => {
    const s = document.querySelector(".sequence");
    const btn = s.querySelector(".play-toggle");
    return {
      pressed: btn.getAttribute("aria-pressed"),
      label: btn.textContent,
      counter: s.querySelector(".stepper .counter").textContent.trim(),
      meta: s.querySelector(".plate .frame-meta").textContent.trim(),
      quality: s.querySelector(".plate .quality")?.textContent.trim() ?? null,
      note: s.querySelector(".play-note")?.textContent ?? null,
      live: s.querySelector('[aria-live="polite"]').textContent,
      src: s.querySelector(".plate .sky img")?.getAttribute("src") ?? null,
    };
  });

async function sample(page, ms, every = 100) {
  const seen = [];
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const s = await state(page);
    if (!seen.length || seen[seen.length - 1].counter !== s.counter) seen.push({ t: Date.now() - t0, ...s });
    await page.waitForTimeout(every);
  }
  return seen;
}

// ---- 1280 desktop
{
  const { ctx, page } = await open(1280, 900);
  await page.locator(".sequence").scrollIntoViewIfNeeded();
  const before = await state(page);
  log("initial", before);
  await page.click(".sequence .play-toggle");
  const seen = await sample(page, 3200);
  log("1280 frames seen in 3.2 s:", seen.length);
  for (const s of seen) log(`  t=${s.t}ms ${s.counter} | ${s.meta} | ${s.quality}`);
  const after = await state(page);
  log("playing state", { pressed: after.pressed, label: after.label, note: after.note, live: after.live });
  log("live-region mutations while playing:", await page.evaluate(() => window.__live));
  await page.locator(".sequence").evaluate((el) => el.scrollIntoView({ block: "start" }));
  await page.screenshot({ path: `${OUT}/play-barnard-1280.jpg`, type: "jpeg", quality: 82 });

  // Stop rules
  const stopCheck = async (name, fn) => {
    if ((await state(page)).pressed !== "true") await page.click(".sequence .play-toggle");
    await page.waitForTimeout(700);
    await fn();
    await page.waitForTimeout(150);
    const a = await state(page);
    await page.waitForTimeout(1200);
    const b = await state(page);
    log(`stop on ${name}:`, a.pressed === "false" && a.counter === b.counter ? "PASS" : "FAIL", a.pressed, a.counter, b.counter);
  };
  await stopCheck("hidden tab", () =>
    page.evaluate(() => {
      Object.defineProperty(document, "hidden", { value: true, configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
      delete document.hidden;
    }),
  );
  await stopCheck("print", () => page.evaluate(() => window.dispatchEvent(new Event("beforeprint"))));
  await stopCheck("manual step (ArrowRight)", async () => {
    await page.focus(".sequence .play-toggle");
    await page.keyboard.press("ArrowRight");
  });
  await stopCheck("Pause click", () => page.click(".sequence .play-toggle"));
  await stopCheck("breakpoint crossing 1280→540", () => page.setViewportSize({ width: 540, height: 900 }));
  await page.setViewportSize({ width: 1280, height: 900 });
  // Keyboard: Space toggles via native button
  await page.focus(".sequence .play-toggle");
  await page.keyboard.press("Space");
  await page.waitForTimeout(200);
  log("Space starts play:", (await state(page)).pressed);
  await page.keyboard.press("Space");
  await page.waitForTimeout(200);
  log("Space pauses:", (await state(page)).pressed);
  // Footer AI line
  log(
    "footer:",
    await page.evaluate(() => {
      const a = document.querySelector("footer .footer-ai a");
      return a && { text: a.textContent.replace(/\s+/g, " ").trim(), href: a.href, h: a.getBoundingClientRect().height };
    }),
  );
  await page.locator("footer").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}/footer-ai-1280.jpg`, type: "jpeg", quality: 82, clip: await page.locator("footer").boundingBox() });
  log("overflow 1280:", await page.evaluate(() => document.documentElement.scrollWidth));
  await ctx.close();
}

// ---- 390 phone
{
  const { ctx, page } = await open(390, 844);
  await page.click(".sequence .play-toggle");
  await page.waitForTimeout(1600);
  await page.locator(".sequence").evaluate((el) => el.scrollIntoView({ block: "start" }));
  await page.waitForTimeout(300);
  const s = await state(page);
  log("390 playing", s.pressed, s.counter, s.meta);
  await page.screenshot({ path: `${OUT}/play-barnard-390.jpg`, type: "jpeg", quality: 82 });
  // Three consecutive played frames at 390, same grid, labels changing.
  for (let k = 0; k < 3; k++) {
    await page.waitForTimeout(500);
    await page.locator(".sequence .sequence-stage .plate").screenshot({ path: `${OUT}/play-barnard-390-frame${k + 1}.jpg`, type: "jpeg", quality: 80 });
  }
  log(
    "390 targets:",
    await page.evaluate(() => {
      const b = document.querySelector(".sequence .play-toggle").getBoundingClientRect();
      return { w: b.width, h: b.height, scrollWidth: document.documentElement.scrollWidth };
    }),
  );
  await page.locator("footer").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}/footer-ai-390.jpg`, type: "jpeg", quality: 82, clip: await page.locator("footer").boundingBox() });
  await ctx.close();
}

// ---- reduced motion
{
  const { ctx, page } = await open(1280, 900, true);
  const s0 = await state(page);
  await page.waitForTimeout(1500);
  const s1 = await state(page);
  log("reduced: paused on load", s0.pressed, "no auto-advance:", s0.counter === s1.counter);
  await page.click(".sequence .play-toggle");
  const seen = await sample(page, 4800);
  const gaps = seen.slice(1).map((s, i) => s.t - seen[i].t);
  log("reduced cadence gaps (ms):", gaps.slice(1));
  await ctx.close();
}

await browser.close();
