// axe-core scan (WCAG 2.0/2.1/2.2 A + AA tags) of key routes and states. Dev-only; nothing is bundled.
import { chromium } from "playwright-core";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const axePath = require.resolve("axe-core/axe.min.js");
const BASE = process.env.BASE || "http://localhost:5195/";
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const cases = [
  { route: "?", w: 1280 },
  { route: "?preset=epsilon_indi_b", w: 1280, open: true },
  { route: "?preset=epsilon_indi_b", w: 390, open: true },
  { route: "?preset=barnards_star", w: 390, open: true },
  { route: "?preset=wise_0855", w: 1280, open: true },
  { route: "?view=query", w: 390, invalid: true },
];
let total = 0;
for (const c of cases) {
  const page = await (await browser.newContext({ viewport: { width: c.w, height: 900 } })).newPage();
  await page.goto(BASE + c.route, { waitUntil: c.route.includes("query") ? "load" : "networkidle" });
  await page.waitForTimeout(1000);
  if (c.open) await page.evaluate(() => document.querySelectorAll("details").forEach((d) => (d.open = true)));
  if (c.invalid) {
    await page.getByLabel("Right ascension").fill("400");
    await page.getByRole("button", { name: "Search the archive" }).click();
  }
  await page.addScriptTag({ path: axePath });
  const res = await page.evaluate(async () =>
    window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } }),
  );
  total += res.violations.length;
  console.log(`\n${c.route} @${c.w}${c.open ? " (details open)" : ""}${c.invalid ? " (invalid input)" : ""}: ${res.violations.length} violations, ${res.passes.length} passing rules, ${res.incomplete.length} needs-review`);
  for (const v of res.violations) {
    console.log(`  [${v.impact}] ${v.id}: ${v.help}`);
    for (const n of v.nodes.slice(0, 4)) console.log(`     ${n.target.join(" ")} :: ${n.failureSummary?.split("\n").slice(1, 2).join(" ")}`);
  }
  if (process.env.INCOMPLETE)
    for (const v of res.incomplete) console.log(`  (review) ${v.id}: ${v.nodes.length} nodes: ${[...new Set(v.nodes.map((n) => n.target.join(" ").split(" ").pop() + " — " + (n.any[0]?.data?.messageKey || n.any[0]?.message || "").slice(0, 60)))].slice(0, 8).join("; ")}`);
}
console.log("\nTOTAL violations:", total);
await browser.close();
