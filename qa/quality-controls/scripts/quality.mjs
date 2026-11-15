// Worker 13: the four quality states at 390 px, each reached by keyboard,
// plus failed / not-loaded marking in the stepper and blink picker (fixture).
import { chromium } from "playwright-core";
const BASE = process.env.BASE ?? "http://localhost:5200/";
const OUT = process.env.OUT ?? ".";
const W = Number(process.env.W ?? 390);
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const log = (...a) => console.log(...a);

async function open(route) {
  const ctx = await browser.newContext({ viewport: { width: W, height: 844 } });
  const page = await ctx.newPage();
  await page.goto(BASE + route);
  await page.waitForSelector(".sequence .wave-filter select", { timeout: 60000 });
  await page.waitForFunction(() => document.querySelectorAll(".sequence .plate .sky img").length > 0, null, { timeout: 60000 });
  return { ctx, page };
}

const read = (page) =>
  page.evaluate(() => {
    const s = document.querySelector(".sequence");
    const side = s.querySelector(".sequence-side");
    const det = side.querySelector("details.panel");
    return {
      frame: side.querySelector(".facts .mono")?.textContent ?? null,
      plateChip: s.querySelector(".plate .quality")?.textContent.trim() ?? null,
      plateStatus: s.querySelector(".plate .quality")?.dataset.status ?? null,
      plateMeta: s.querySelector(".plate .frame-meta").innerText.replace(/\n/g, " | "),
      plateFoot: s.querySelector(".plate .plate-foot").innerText.replace(/\n/g, " | "),
      plateNote: s.querySelector(".plate .plate-note")?.textContent ?? null,
      explanation: side.querySelector(":scope > p")?.innerText ?? null,
      wavelength: [...side.querySelectorAll(".facts > div")].find((d) => d.querySelector("dt")?.textContent === "Wavelength")?.querySelector("dd").textContent,
      detailsOpen: det?.open ?? null,
      qualityDetails: det ? det.querySelector(".details-body").innerText.replace(/\n/g, " | ") : null,
      banner: document.querySelector(".fixture-banner")?.innerText ?? null,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      focus: document.activeElement.textContent.trim().slice(0, 40),
    };
  });

async function openQualityByKeyboard(page) {
  await page.focus(".sequence .sequence-side details.panel > summary");
  // The disclosure keeps its state between frames; only open it if closed.
  if (!(await page.locator(".sequence .sequence-side details.panel").first().evaluate((d) => d.open))) {
    await page.keyboard.press("Enter");
  }
}

async function shot(page, name) {
  // Tall element captures stitch past the viewport, where the fixed, off-screen
  // skip link would otherwise be drawn into the image. Screenshot-only style.
  await page.addStyleTag({ content: ".skip{display:none}" });
  await page.locator(".sequence .sequence-side").evaluate((el) => el.scrollIntoView({ block: "start" }));
  await page.locator(".sequence .sequence-body").screenshot({ path: `${OUT}/${name}`, type: "jpeg", quality: 80 });
}

// clear: Epsilon Indi B case frame A, by keyboard (Frame A button, Enter).
{
  const { ctx, page } = await open("?preset=epsilon_indi_b");
  await page.focus(".sequence .ref-jump button");
  await page.keyboard.press("Enter");
  await openQualityByKeyboard(page);
  log("CLEAR", await read(page));
  await shot(page, `quality-clear-${W}.jpg`);
  // not_covered: Home from the stepper goes to frame #1 (2025W17_4B_0077_2_D1).
  await page.focus(".sequence .stepper button[aria-label='Earlier frame']");
  await page.keyboard.press("Home");
  await openQualityByKeyboard(page);
  log("NOT_COVERED", await read(page));
  await shot(page, `quality-not-covered-${W}.jpg`);
  // Filter excludes it and counts it: choose Near on frame A, then report.
  await page.focus(".sequence .ref-jump button");
  await page.keyboard.press("Enter");
  await page.focus(".sequence .wave-filter select");
  await page.keyboard.type("N");
  log("EPS near-filter summary:", await page.locator(".sequence .wave-filter-summary").innerText());
  await ctx.close();
}

// flagged: Barnard's Star case frame A.
{
  const { ctx, page } = await open("?preset=barnards_star");
  await page.focus(".sequence .ref-jump button");
  await page.keyboard.press("Enter");
  await openQualityByKeyboard(page);
  log("FLAGGED", await read(page));
  await shot(page, `quality-flagged-${W}.jpg`);
  await ctx.close();
}

// unknown: development fixture only (no real product has one), via a fixture search.
{
  const { ctx, page } = await open("?view=query&ra=331.0967&dec=-56.8006&fov=6&fixtures=1");
  // Wait until every fixture frame has settled (ready or failed).
  await page.waitForFunction(
    () => [...document.querySelectorAll(".sequence .pair-picker select")[0]?.options ?? []].every((o) => !/loading|not loaded yet/.test(o.textContent)),
    null,
    { timeout: 30000 },
  );
  await page.waitForTimeout(300);
  const options = await page.$$eval(".sequence .pair-picker select:first-of-type option", (os) => os.map((o) => `${o.textContent}${o.disabled ? " (disabled)" : ""}`));
  log("FIXTURE blink options:", options);
  // Step by keyboard until the unknown-quality fixture frame is shown.
  await page.focus(".sequence .stepper button[aria-label='Earlier frame']");
  await page.keyboard.press("Home");
  const visited = [];
  for (let i = 0; i < 6; i++) {
    const r = await page.evaluate(() => ({
      counter: document.querySelector(".sequence .stepper .counter").textContent.trim(),
      valuetext: document.querySelector('.sequence .stepper input[type="range"]').getAttribute("aria-valuetext"),
      key: document.querySelector(".sequence .sequence-side .facts .mono")?.textContent ?? null,
      placeholder: document.querySelector(".sequence .plate .sky-empty")?.innerText ?? null,
    }));
    visited.push(r);
    if (r.key === "FIXTURE_UNKNOWN_QUALITY_D2") break;
    await page.keyboard.press("ArrowRight");
  }
  log("FIXTURE stepper walk:", visited);
  await openQualityByKeyboard(page);
  log("UNKNOWN", await read(page));
  await shot(page, `quality-unknown-fixture-${W}.jpg`);
  // Failed-frame marking: step to the failed fixture frame and screenshot the stepper.
  await page.focus(".sequence .stepper button[aria-label='Earlier frame']");
  await page.keyboard.press("ArrowLeft");
  log("FAILED frame counter:", await page.locator(".sequence .stepper .counter").innerText());
  await page.locator(".sequence .stepper").evaluate((el) => el.scrollIntoView({ block: "start", behavior: "instant" }));
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/failed-frame-marked-${W}.jpg`, type: "jpeg", quality: 80 });
  // Choose the failed frame in the blink picker by keyboard (type-ahead "#3").
  const first = page.locator(".sequence .pair-picker select").first();
  const failedValue = await first.evaluate((sel) => [...sel.options].find((o) => /failed/.test(o.textContent))?.value);
  await first.selectOption(failedValue);
  log("pair summary with failed frame:", await page.locator(".sequence .pair-picker .pair-summary").first().innerText());
  log("Blink disabled:", await page.locator(".sequence .pair-picker button").getAttribute("disabled"));
  await page.locator(".sequence .pair-picker").screenshot({ path: `${OUT}/blink-picker-failed-${W}.jpg`, type: "jpeg", quality: 80 });
  // Filter counts on the fixture: frame A, Near.
  await page.focus(".sequence .stepper button[aria-label='Earlier frame']");
  await page.keyboard.press("Home");
  await page.focus(".sequence .wave-filter select");
  await page.keyboard.type("N");
  log("FIXTURE near-filter summary:", await page.locator(".sequence .wave-filter-summary").innerText());
  await ctx.close();
}
await browser.close();
