// Coordinate form: labels, descriptions, error association, focus on first invalid field, overflow.
import { chromium } from "playwright-core";
const BASE = process.env.BASE || "http://localhost:5195/";
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
for (const width of [320, 390]) {
  const page = await (await browser.newContext({ viewport: { width, height: 844 } })).newPage();
  await page.goto(BASE + "?view=query", { waitUntil: "load" });
  await page.waitForSelector("form.query-form");
  const fields = await page.evaluate(() =>
    [...document.querySelectorAll(".query-fields input")].map((i) => ({
      label: document.querySelector(`label[for="${CSS.escape(i.id)}"]`)?.textContent,
      describedby: (i.getAttribute("aria-describedby") || "")
        .split(" ")
        .map((id) => document.getElementById(id)?.textContent)
        .join(" | "),
      inputMode: i.inputMode,
    })),
  );
  await page.getByLabel("Right ascension").fill("400");
  await page.getByLabel("Declination").fill("-56.7");
  await page.getByRole("button", { name: "Search the archive" }).click();
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => {
    const ra = document.querySelector(".query-fields input");
    return {
      focused: document.activeElement === ra,
      ariaInvalid: ra.getAttribute("aria-invalid"),
      describedby: (ra.getAttribute("aria-describedby") || "")
        .split(" ")
        .map((id) => document.getElementById(id)?.textContent)
        .join(" | "),
      docW: document.documentElement.scrollWidth,
    };
  });
  console.log(width, JSON.stringify({ fields, after }, null, 1));
  if (process.env.SHOT) await page.screenshot({ path: `${process.env.SHOT}-query-error-${width}.png` });
}
await browser.close();
