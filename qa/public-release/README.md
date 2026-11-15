# Public release verification — 2026-11-15

Codex verified the first production release without a Vercel session or bypass.

- Origin: https://perigee-liard.vercel.app
- Git commit: `ef298900aa5769c47ec32f2bdb7c94ac27af14f3` (PR #27 merge).
- Deployment: `dpl_4gggyXwZGgMaUtSPRUSJx6iJUMjq`; the Vercel API reported production, READY, this Git SHA and the production alias.
- Source: https://github.com/sathvikloke/perigee, now public with Sathvik's approval.
- Smoke: [run 43658316997](https://github.com/sathvikloke/perigee/actions/runs/43658316997), manually dispatched on main with live=true. PASS 20/20 at 00:28:33 UTC; captured output in [smoke.txt](smoke.txt).

## Access and configuration

Unauthenticated GET / returned 200 HTML. GET /api/v1/health returned 200 JSON, status ok, token_signing env. The smoke exercised frontend deep links, catalog/assets, case content, JSON API 404s, a live non-preset search and a processed PNG.

Separate sensitive signing keys were set for Production and Preview before the production build. No secret value was recorded. Standard Protection was already configured and retained. The pre-release preview `perigee-jwe8ny05j-sathviklokes-projects.vercel.app` returned 302 to Vercel login after publication; production returned 200 without login.

## Independent public browser journey

A new in-app browser tab opened the production homepage with an empty saved-evidence list. No development-fixture control was shown.

1. Opened Epsilon Indi B from the target list; 44 curated frames loaded.
2. A+B showed observations 151 days apart at nearly the same wavelength. Switching to A+C changed the second plate and displayed the same-moment, different-wavelength explanation and individual-stretch note.
3. Switched back to A+B and enabled the quality overlay; the checked control and overlay legend appeared.
4. Entered synthetic QA notes in all three fields. The app reported Saved on this device.
5. Exported a real evidence-card JSON download. It includes both frame records, source URLs, SHA-256 hashes, processing metadata, notes and all five case limitations verbatim from the production case endpoint. See [evidence-card-production.json](evidence-card-production.json).
6. Returned Home; the saved list displayed the named investigation and claim excerpt. Reopen returned to Epsilon Indi B and restored all three notes, with Restored from this device shown. [Screenshot](notebook-restored.jpg).
7. Browser console inspection returned no error/warning records for this tab. A production-deployment error/fatal log query at 00:29:51 UTC returned no matching logs. That query is scoped evidence, not a claim that the app can never fail.

The synthetic notebook remains local to the QA browser. It is not a user study or a discovery.

## Limits of this record

This pass did not test a physical phone, assistive screen reader, or every external-source outage. Claude's separate production journey covers additional UI paths and print artifacts. Automatic post-deployment smoke triggering is not established by a manual successful run. Live search remains dependent on NASA/IPAC IRSA availability; curated cases use bundled files.
