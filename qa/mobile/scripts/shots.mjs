// QA evidence screenshots (JPEG) + inline-target pseudo-element check.
import { chromium } from "playwright-core";
const BASE = process.env.BASE || "http://localhost:5195/";
const OUT = process.env.OUT;
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const shot = async (name, route, w, h, opts = {}) => {
  const page = await (await browser.newContext({ viewport: { width: w, height: h }, hasTouch: w < 600 })).newPage();
  await page.goto(BASE + route, { waitUntil: route.includes("query") ? "load" : "networkidle" });
  await page.waitForTimeout(1200);
  if (opts.before) await opts.before(page);
  await page.screenshot({ path: `${OUT}/${name}.jpg`, type: "jpeg", quality: 72, fullPage: !!opts.full });
  if (opts.after) await opts.after(page);
  await page.context().close();
};
await shot("after-desktop-1280", "?preset=epsilon_indi_b", 1280, 900);
await shot("after-tablet-768", "?preset=epsilon_indi_b", 768, 1024);
await shot("after-phone-390", "?preset=epsilon_indi_b", 390, 844);
await shot("after-phone-390-moving-star", "?preset=barnards_star", 390, 844);
await shot("after-phone-320", "?preset=epsilon_indi_b", 320, 700);
await shot("after-phone-390-sources-open", "?preset=epsilon_indi_b", 390, 844, {
  before: async (p) => {
    await p.evaluate(() => {
      const d = document.getElementById("sources");
      d.open = true;
      document.documentElement.style.scrollBehavior = "auto"; d.scrollIntoView();
    });
    await p.waitForTimeout(300);
  },
});
await shot("after-phone-320-sources-open", "?preset=epsilon_indi_b", 320, 700, {
  before: async (p) => {
    await p.evaluate(() => {
      const d = document.getElementById("sources");
      d.open = true;
      document.documentElement.style.scrollBehavior = "auto"; d.scrollIntoView();
    });
    await p.waitForTimeout(300);
  },
});
await shot("after-phone-390-query-error", "?view=query", 390, 844, {
  before: async (p) => {
    await p.getByLabel("Right ascension").fill("400");
    await p.getByRole("button", { name: "Search the archive" }).click();
    await p.waitForTimeout(300);
    await p.evaluate(() => window.scrollTo(0, 0));
  },
});
await shot("after-desktop-1280-focus-blink", "?preset=epsilon_indi_b", 1280, 900, {
  before: async (p) => {
    await p.locator(".blink-toggle").focus();
    await p.keyboard.press("Shift+Tab");
    await p.keyboard.press("Tab");
    await p.waitForTimeout(400);
  },
});
await shot("print-preview-1280", "?preset=epsilon_indi_b", 1280, 900, {
  full: true,
  before: async (p) => {
    const boxes = p.locator(".notebook textarea");
    await boxes.nth(0).fill("A and B are a fair test of change over time.");
    await boxes.nth(1).fill("Both near 2.32 µm, five months apart; both pass the flag screen.");
    await boxes.nth(2).fill("Brightness change needs calibrated photometry.");
    await p.emulateMedia({ media: "print" });
  },
  after: async (p) => {
    await p.pdf({ path: `${OUT}/print-evidence.pdf`, format: "A4", printBackground: true });
  },
});

// ::after hit areas on inline text buttons
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
await page.goto(BASE + "?preset=epsilon_indi_b", { waitUntil: "networkidle" });
console.log(
  await page.evaluate(() =>
    [...document.querySelectorAll("button.link")].map(
      (b) => `${b.textContent.trim().slice(0, 30)}: box ${Math.round(b.getBoundingClientRect().height)}px, hit ${getComputedStyle(b, "::after").height}`,
    ),
  ),
);
await browser.close();
