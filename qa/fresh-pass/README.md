# Fresh-user QA pass — 2026-11-14 (Neeraj, issue #6)

**Tested:** `claude/perigee-integration` @ `cc2c3ca`, run **locally** (uvicorn `PERIGEE_DEV_MODE=1` on :8000, Vite dev on :5173, viewport 1024×768). Live searches went to the real NASA/IPAC IRSA archive.
**Not tested:** any deployed URL (all are behind Vercel login, see B1), phone viewport, keyboard-only, print, Barnard's Star case.

## Blockers (judges can't reach the project)

| # | Finding | Evidence | Owner |
|---|---|---|---|
| B1 | **No public app.** Every Vercel URL redirects logged-out visitors to Vercel login. | `curl` (logged out) on `perigee-git-claude-perigee-integration-sathviklokes-projects.vercel.app/`, `/api/v1/health` and `perigee-sathviklokes-projects.vercel.app/`: all `302 → vercel.com/sso-api`. | Suhrit / Sathvik (production promotion + turn off Vercel Authentication for production only) |
| B2 | **Repo is private.** `github.com/sathvikloke/perigee` returns 404 to logged-out visitors, and so does the app footer link `…/blob/main/docs/AI_USE.md`. That file also isn't on `main` yet, only on the integration branch. | `curl` status 404 for both URLs. | Sathvik (make the repo public or submit a public mirror; merge #27 so `AI_USE.md` is on `main`) |

Reminder from PR #27: `perigee.vercel.app` (200 OK) is an **unrelated third-party app**. Don't submit it.

## Core journey (local): works

1. **Home** loads with 5 presets, frame counts and the guided/free labels. ✔
2. **Epsilon Indi B "Is this a fair comparison?"** shows A/B dates, wavelengths, flag screen, the "catalog prediction, not a detection" label, and the date gap and wavelength difference. ✔ ([screenshot](epsindi-case-1024.jpg))
3. **Notebook → Export.** I wrote a claim with quotes, an apostrophe, `&` and a line break. The exported `perigee-evidence-fair_comparison-…json` kept the text exactly, plus frame/observation IDs, UTC dates, MJD, wavelengths with location, quality status, SHA-256, IRSA source URLs and 4 source links. ✔
4. **Reload:** all three notebook fields came back, and the card is listed under My evidence. ✔
5. **"Check your claim against the case guide"** (the README said this was untested) expands and shows the supported claims, the unsupported claims and an example claim. ✔
6. **Invalid coordinates** (RA `400`, Dec `12abc`): rejected before any request was sent, with a clear message per field. ✔
7. **Non-preset live search** RA 83.82, Dec −5.39 (Orion Nebula), limit 6: 6 of 377 matches, shown in time order, labelled "shortened by the result limit". 5 frames processed (all "Flagged near target", which is expected for a saturated nebula core). ✔ ([screenshot](live-search-orion-1024.jpg))
8. **Upstream failure:** the archive returned `502 UPSTREAM_UNAVAILABLE` for frame 4. It stayed in date order and showed "The NASA/IPAC archive could not provide this image right now" with a **Retry this frame** button. The other frames were unaffected. ✔

## Findings

| # | Severity | Finding | Repro | Owner |
|---|---|---|---|---|
| F1 | Medium | **The exported evidence card has no limitations.** The API supplies `limitations` for the case and for each frame (e.g. "not photometry", "QR products may be reprocessed"), but the JSON export only carries the learner's own `uncertainty` text. Once the export leaves the app, nothing says the stretch is display-only or that the marker is a prediction. | Export from `?preset=epsilon_indi_b` and look for `limitations`: there is none. Compare `GET /api/v1/cases/fair_comparison` → `limitations` (4 items). `frontend/src/evidence/card.ts` | Akshobya (wording decision: Sathvik) |
| F2 | Low / external | **SIMBAD links return 404** in the case sources (`simbad/sim-id?Ident=eps+Ind+B`, `…Barnard%27s+star`). The whole SIMBAD web UI 404s right now, even `sim-id?Ident=Vega` and `/simbad/`, while the CDS Sesame links work. This looks like a CDS outage, not our URLs. **Recheck Sunday morning**, and if it's still down, link the Sesame resolver instead. | Open the links in a browser: CDS "Page unavailable" 404. | Sathvik |
| F3 | Low | The **My evidence** list titles the card with the raw ID `fair_comparison` instead of the case title, and it only offers Export / Delete. There's no way to reopen the card from the list (you have to go back to the target). | Home → My evidence | Akshobya |
| F4 | Note | The same frame A is labelled "shared stretch" in the case pair (case asset) but "own contrast stretch" in the timeline below it. Both are correct, because they are different renderings. A learner may still find it confusing that the same frame gets two brightness statements. | `?preset=epsilon_indi_b`, compare the pair with timeline frame 35 | Akshobya (optional) |

Checked and fine: the "Use development fixture" button only appears in dev builds (`import.meta.env.DEV`). An unknown `/api/v1/*` route returns a JSON 404, not SPA HTML.

## Submission link check (logged out, 31 links from README, PITCH, AI_USE, case JSON, frontend)

- **Fail:** repo (404, private), `docs/AI_USE.md` on main (404), the 2 SIMBAD `sim-id` links (404, see F2), all Vercel app URLs (login wall).
- **OK in a browser:** JPL "Interstellar glaciers" (curl gets a 403 from bot blocking; it loads fine in a real browser).
- **200:** every IRSA mission/doc page, all 6 case FITS source URLs, IRSA tutorial, Sesame resolvers, Gaia, NASA brown-dwarf article, Space Apps challenge/team/judging/submission pages, Rubin, Zooniverse.

## Rerun on the deployed build

Once a public URL exists, repeat steps 1–8 in a private window on that URL and record the deployed commit. Also check that `/api/v1/health` returns JSON and that `token_signing` is **not** `dev_fallback`.
