// Keyboard path, focus visibility, stepper focus retention, live-region chatter, reduced motion.
import { chromium } from "playwright-core";
const BASE = process.env.BASE || "http://localhost:5195/";
const route = process.env.ROUTE || "?preset=epsilon_indi_b";
const width = Number(process.env.W || 1280);
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const ctx = await browser.newContext({
  viewport: { width, height: 900 },
  reducedMotion: process.env.RM ? "reduce" : "no-preference",
});
const page = await ctx.newPage();
await page.goto(BASE + route, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

const describe = () =>
  page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { name: "<body>" };
    const cs = getComputedStyle(el);
    const b = el.getBoundingClientRect();
    const name = (el.getAttribute("aria-label") || el.textContent || el.id || "").replace(/\s+/g, " ").trim().slice(0, 48);
    return {
      name: `${el.tagName.toLowerCase()}${el.type ? `[${el.type}]` : ""} "${name}"`,
      outline: `${cs.outlineStyle} ${cs.outlineWidth}`,
      inView: b.bottom > 0 && b.top < innerHeight,
    };
  });

// 1. Tab order
const seen = [];
let prev = "";
let repeats = 0;
for (let i = 0; i < Number(process.env.TABS || 60); i++) {
  await page.keyboard.press("Tab");
  const d = await describe();
  const line = `${String(i + 1).padStart(2)} ${d.name} | focus ${d.outline} | inView ${d.inView}`;
  seen.push(line);
  if (d.name === prev) repeats++;
  prev = d.name;
  if (d.name === "<body>") break;
}
console.log("TAB ORDER\n" + seen.join("\n"));
console.log("consecutive repeats (trap indicator):", repeats);
const noOutline = seen.filter((l) => l.includes("focus none") && !l.includes("<body>"));
console.log("focused without outline:", noOutline.length ? noOutline : "none");

// 2. Reduced motion / blink initial state
const blink = await page.evaluate(() => {
  const b = [...document.querySelectorAll("button")].find((x) => /Blink/.test(x.textContent));
  return b ? { text: b.textContent.trim(), pressed: b.getAttribute("aria-pressed") } : null;
});
const motion = await page.evaluate(() => ({
  scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
  buttonTransition: getComputedStyle(document.querySelector("button")).transitionDuration,
  blinkingPlates: document.querySelectorAll(".plates.blinking").length,
}));
console.log("blink initial:", JSON.stringify(blink), "motion:", JSON.stringify(motion));

// 3. Stepper: focus Later, press End, check focus kept; ArrowLeft steps back
const later = page.getByRole("button", { name: "Later frame" });
if (await later.count()) {
  await later.focus();
  const before = await page.locator(".sequence .counter[aria-hidden]").textContent();
  await page.keyboard.press("End");
  const atEnd = await page.locator(".sequence .counter[aria-hidden]").textContent();
  const focusAfterEnd = (await describe()).name;
  await page.keyboard.press("ArrowLeft");
  const afterLeft = await page.locator(".sequence .counter[aria-hidden]").textContent();
  await page.keyboard.press("Home");
  const atHome = await page.locator(".sequence .counter[aria-hidden]").textContent();
  const earlierFocus = await page.getByRole("button", { name: "Earlier frame" });
  await earlierFocus.focus();
  await page.keyboard.press("Enter"); // at index 0: must be a no-op and keep focus
  const focusAtStart = (await describe()).name;
  console.log("STEPPER", { before, atEnd, focusAfterEnd, afterLeft, atHome, focusAtStart });
}

// 4. Live-region chatter during case blink
const caseBlink = page.locator(".blink-toggle, .pair-picker button").first();
if (await caseBlink.count()) {
  await page.evaluate(() => {
    window.__liveChanges = 0;
    const regions = [...document.querySelectorAll("[aria-live]:not([aria-live=off]), [role=status]")];
    const mo = new MutationObserver(() => window.__liveChanges++);
    regions.forEach((r) => mo.observe(r, { childList: true, subtree: true, characterData: true }));
  });
  await caseBlink.click();
  await page.waitForTimeout(3500);
  const alternations = await page.evaluate(() => window.__liveChanges);
  await caseBlink.click();
  console.log("live-region mutations during 3.5s of case blink:", alternations);
}
await browser.close();
