// Print preview of the evidence card: emulate print media, check required provenance text, save PDF + screenshot.
import { chromium } from "playwright-core";
const BASE = process.env.BASE || "http://localhost:5195/";
const OUT = process.env.OUT || ".";
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
await page.goto(BASE + "?preset=epsilon_indi_b", { waitUntil: "networkidle" });
await page.waitForTimeout(1000);
const long =
  "A long note to test wrapping: " + "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr/level2/2026W17_1A/l2b-v20-2026-118/3/level2_2026W17_1A_0123_4D3_spx_l2b-v20-2026-118.fits ".repeat(2);
const boxes = page.locator(".notebook textarea");
await boxes.nth(0).fill("A and B are a fair test of change over time.");
await boxes.nth(1).fill(long);
await boxes.nth(2).fill("Line one of uncertainty.\nLine two: brightness needs calibrated photometry.");
await page.emulateMedia({ media: "print" });
const text = await page.evaluate(() => document.body.innerText);
const card = await page.evaluate(() => {
  const s = document.querySelector(".print-provenance");
  return s ? s.innerText : "";
});
const checks = {
  frameIds: /Observation A · \S+/.test(card) && /Observation B · \S+/.test(card),
  detector: /Detector: \d/.test(card),
  release: /Release: \S+/.test(card),
  utc: /UTC: \d{4}-\d\d-\d\d|UTC: \d/.test(card),
  wavelength: /Wavelength: [\d.]+ µm/.test(card),
  sourceUrl: /Source: https?:\/\//.test(card),
  processing: /Processing: /.test(card),
  claim: text.includes("A and B are a fair test"),
  longNote: text.includes("level2_2026W17_1A_0123_4D3"),
  multiLineNote: text.includes("Line two: brightness"),
  bothPlates: await page.evaluate(() => [...document.querySelectorAll(".plate")].filter((p) => p.offsetParent).length),
  overflow: await page.evaluate(() => document.documentElement.scrollWidth),
};
console.log(JSON.stringify(checks, null, 1));
console.log("--- printed provenance ---\n" + card);
await page.pdf({ path: `${OUT}/print-evidence.pdf`, format: "A4", printBackground: true });
await page.screenshot({ path: `${OUT}/print-preview-1280.png`, fullPage: true });
await browser.close();
