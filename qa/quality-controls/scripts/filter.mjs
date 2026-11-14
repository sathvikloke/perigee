// Worker 13: wavelength filter on Barnard's Star. Play only visits frames near
// case frame A's wavelength; screenshots at 1280 and 390; keyboard path.
import { chromium } from "playwright-core";
const BASE = process.env.BASE ?? "http://localhost:5200/";
const OUT = process.env.OUT ?? ".";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const log = (...a) => console.log(...a);

const state = (page) =>
  page.evaluate(() => {
    const s = document.querySelector(".sequence");
    return {
      pressed: s.querySelector(".play-toggle").getAttribute("aria-pressed"),
      counter: s.querySelector(".stepper .counter").textContent.trim(),
      meta: s.querySelector(".plate .frame-meta").textContent.trim(),
      heading: s.querySelector(".plate h3").textContent.trim(),
      quality: s.querySelector(".plate .quality")?.textContent.trim() ?? null,
      note: s.querySelector(".play-note")?.textContent ?? null,
      live: s.querySelector('.stepper ~ [aria-live="polite"]')?.textContent ?? null,
      summary: s.querySelector(".wave-filter-summary")?.innerText ?? null,
      filter: s.querySelector(".wave-filter select").value,
      options: [...s.querySelectorAll(".wave-filter option")].map((o) => `${o.value}${o.disabled ? "(disabled)" : ""}: ${o.textContent}`),
      valuetext: s.querySelector('.stepper input[type="range"]').getAttribute("aria-valuetext"),
    };
  });

async function sample(page, ms, every = 80) {
  const seen = [];
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const s = await state(page);
    if (!seen.length || seen[seen.length - 1].meta !== s.meta || seen[seen.length - 1].heading !== s.heading) seen.push({ t: Date.now() - t0, ...s });
    await page.waitForTimeout(every);
  }
  return seen;
}

async function open(width, height) {
  const ctx = await browser.newContext({ viewport: { width, height } });
  const page = await ctx.newPage();
  await page.goto(BASE + "?preset=barnards_star");
  await page.waitForSelector(".sequence .wave-filter select", { timeout: 60000 });
  await page.waitForFunction(() => document.querySelectorAll(".sequence .plate img").length > 0, null, { timeout: 60000 });
  return { ctx, page };
}

for (const [w, h] of [
  [1280, 900],
  [390, 844],
]) {
  const { ctx, page } = await open(w, h);
  // Go to case frame A with its jump button.
  await page.locator(".sequence .ref-jump button", { hasText: "Frame A" }).click();
  log(`\n== ${w}px: on frame A`, await state(page));
  await page.selectOption(".sequence .wave-filter select", "near");
  const s1 = await state(page);
  log("near filter:", { counter: s1.counter, summary: s1.summary, options: s1.options });
  await page.click(".sequence .play-toggle");
  const seen = await sample(page, 3400);
  log(`${w} frames seen while playing 3.4 s:`);
  for (const s of seen) log(`  t=${s.t}ms ${s.counter} | ${s.heading} | ${s.meta} | ${s.quality}`);
  const p = await state(page);
  log("while playing:", { note: p.note, live: p.live });
  // Screenshot while playing, sequence in view.
  await page.locator(".sequence").evaluate((el) => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${OUT}/play-filtered-barnard-${w}.jpg`, type: "jpeg", quality: 82 });
  await page.click(".sequence .play-toggle");
  // Detector option
  await page.locator(".sequence .ref-jump button", { hasText: "Frame A" }).click();
  await page.selectOption(".sequence .wave-filter select", "all");
  await page.selectOption(".sequence .wave-filter select", "detector");
  log("detector filter:", (await state(page)).summary);
  await page.selectOption(".sequence .wave-filter select", "all");
  log("all:", (await state(page)).counter);
  const overflow = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  log("scrollWidth vs viewport", overflow);
  const box = await page.locator(".sequence .wave-filter select").boundingBox();
  log("select box", box);
  await ctx.close();
}

// The keyboard path is in keyboard.mjs.
await browser.close();
