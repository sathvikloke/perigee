// Worker 13: keyboard-only path through the wavelength filter and Play on Barnard's Star.
import { chromium } from "playwright-core";
const BASE = process.env.BASE ?? "http://localhost:5200/";
const W = Number(process.env.W ?? 1280);
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: W, height: 900 } });
const page = await ctx.newPage();
await page.goto(BASE + "?preset=barnards_star");
await page.waitForSelector(".sequence .wave-filter select", { timeout: 60000 });
await page.waitForFunction(() => document.querySelectorAll(".sequence .plate img").length > 0, null, { timeout: 60000 });
const st = () =>
  page.evaluate(() => {
    const s = document.querySelector(".sequence");
    const a = document.activeElement;
    return {
      focus: `${a.tagName.toLowerCase()} "${(a.getAttribute("aria-label") || a.textContent || "").trim().slice(0, 40)}"`,
      focusOutline: getComputedStyle(a).outlineStyle + " " + getComputedStyle(a).outlineWidth,
      filter: s.querySelector(".wave-filter select").value,
      counter: s.querySelector(".stepper .counter").textContent.trim(),
      heading: s.querySelector(".plate h3").textContent.trim(),
      meta: s.querySelector(".plate .frame-meta").textContent.trim(),
      pressed: s.querySelector(".play-toggle").getAttribute("aria-pressed"),
      summary: s.querySelector(".wave-filter-summary")?.innerText ?? null,
      live: s.querySelector('.stepper ~ [aria-live="polite"]').textContent,
    };
  });
const log = (...a) => console.log(...a);

// 1. Keyboard only, starting from the "Frame A" jump button.
await page.focus(".sequence .ref-jump button");
await page.keyboard.press("Enter");
log("Enter on Frame A:", await st());
// 2. Shift+Tab back to the filter select.
let n = 0;
while ((await page.evaluate(() => document.activeElement.tagName)) !== "SELECT" && n++ < 15) await page.keyboard.press("Shift+Tab");
log(`Shift+Tab x${n} ->`, (await st()).focus, (await st()).focusOutline);
// 3. Type-ahead on the closed native select ("N" = Near ...).
await page.keyboard.type("N");
log("type N on select:", await st());
// 4. Shift+Tab to Play (Later, slider, Earlier, Play).
for (let i = 0; i < 4; i++) await page.keyboard.press("Shift+Tab");
log("focus:", (await st()).focus, (await st()).focusOutline);
await page.keyboard.press("Space");
await page.waitForTimeout(1600);
log("Space (play):", await st());
await page.keyboard.press("Space");
log("Space (pause):", await st());
// 5. Arrow keys and Home/End stay inside the filter.
for (const k of ["ArrowRight", "ArrowRight", "ArrowRight", "ArrowLeft", "Home", "End"]) {
  await page.keyboard.press(k);
  const s = await st();
  log(k.padEnd(10), s.counter, "|", s.heading, "|", s.meta);
}
// 6. Slider by keyboard.
await page.focus('.sequence .stepper input[type="range"]');
await page.keyboard.press("ArrowLeft");
const s2 = await st();
log("slider ArrowLeft:", s2.counter, s2.heading, "| valuetext:", await page.getAttribute('.sequence .stepper input[type="range"]', "aria-valuetext"));
// 7. Back to all wavelengths.
await page.focus(".sequence .wave-filter select");
await page.keyboard.type("A");
const s3 = await st();
log("type A:", s3.filter, s3.counter, s3.summary);
await browser.close();
