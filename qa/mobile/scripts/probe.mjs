import { chromium } from "playwright-core";
const BASE = process.env.BASE || "http://localhost:5195/";
const routes = (process.env.ROUTES || "?preset=epsilon_indi_b").split(",");
const widths = (process.env.WIDTHS || "390").split(",").map(Number);
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
for (const route of routes)
  for (const w of widths) {
    const ctx = await browser.newContext({
      viewport: { width: w, height: w < 600 ? 844 : 900 },
      hasTouch: w < 600,
      reducedMotion: process.env.RM ? "reduce" : "no-preference",
    });
    const page = await ctx.newPage();
    await page.goto(BASE + route, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    if (process.env.OPEN) await page.evaluate(() => document.querySelectorAll("details").forEach((d) => (d.open = true)));
    const r = await page.evaluate(() => {
      const out = {};
      out.docW = document.documentElement.scrollWidth;
      out.vw = innerWidth;
      const sky = [...document.querySelectorAll(".sky")].find((e) => e.offsetParent);
      out.firstSkyTop = sky ? Math.round(sky.getBoundingClientRect().top + scrollY) : null;
      out.skyVisiblePx = sky ? Math.max(0, Math.round(innerHeight - sky.getBoundingClientRect().top)) : null;
      const small = [];
      for (const el of document.querySelectorAll("a,button,input,select,textarea,summary")) {
        if (!el.offsetParent && getComputedStyle(el).position !== "fixed") continue;
        const b = el.getBoundingClientRect();
        if (!b.width) continue;
        let h = b.height,
          ww = b.width;
        const lab = el.closest("label");
        if (lab) {
          const lb = lab.getBoundingClientRect();
          h = Math.max(h, lb.height);
          ww = Math.max(ww, lb.width);
        }
        if (h < 44 && !el.closest("details:not([open])")) {
          // Effective pointer target: scan vertically through the centre with elementFromPoint.
          el.scrollIntoView({ block: "center" });
          const c = el.getBoundingClientRect();
          const cx = c.left + c.width / 2;
          let hit = 0;
          for (let y = c.top + c.height / 2 - 30; y <= c.top + c.height / 2 + 30; y++) {
            const t = document.elementFromPoint(cx, y);
            if (t && (t === el || el.contains(t))) hit++;
          }
          h = Math.max(h, hit);
        }
        if (h < 44 || ww < 44)
          small.push(
            `${el.tagName.toLowerCase()}${el.className ? "." + String(el.className).split(" ")[0] : ""}[${el.type || ""}] "${(el.textContent || el.getAttribute("aria-label") || el.name || el.id || "").trim().slice(0, 40)}" ${Math.round(ww)}x${Math.round(h)}`,
          );
      }
      out.small = small;
      const wide = [];
      for (const el of document.querySelectorAll("body *")) {
        const b = el.getBoundingClientRect();
        if (b.right > innerWidth + 1 && b.width && !el.closest(".table-scroll") && !el.closest(".visually-hidden"))
          wide.push(`${el.tagName}.${el.className} r=${Math.round(b.right)}`);
      }
      out.overflowing = wide.slice(0, 12);
      out.nav = [...document.querySelectorAll(".topbar nav a")].map((a) => JSON.stringify(a.textContent));
      return out;
    });
    console.log(route, w, JSON.stringify(r, null, 1));
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(200);
    if (process.env.SHOT)
      await page.screenshot({ path: `${process.env.SHOT}-${w}.png`, fullPage: !!process.env.FULL });
    await ctx.close();
  }
await browser.close();
