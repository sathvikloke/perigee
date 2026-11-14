import { chromium } from "playwright-core";
const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
for (const w of [320, 390, 768]) {
  const p = await (await b.newContext({ viewport: { width: w, height: 844 } })).newPage();
  await p.goto("http://localhost:5198/" + (process.env.ROUTE ?? "?preset=barnards_star"));
  await p.waitForSelector(".sequence .play-toggle", { timeout: 60000 });
  await p.click(".sequence .play-toggle");
  await p.waitForTimeout(1200);
  const r = await p.evaluate(() =>
    [...document.querySelectorAll(".sequence .stepper > *")]
      .map((e) => {
        const b = e.getBoundingClientRect();
        return `${e.className || e.tagName}:${Math.round(b.left)},${Math.round(b.top)} ${Math.round(b.width)}x${Math.round(b.height)}`;
      })
      .concat(["sw=" + document.documentElement.scrollWidth]),
  );
  console.log(w, r.join(" | "));
}
await b.close();
