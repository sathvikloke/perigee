# Cartoon and content-motion release — 15 November 2026

Public app: https://perigee.lokesathvik.workers.dev/

- Merged PR: https://github.com/sathvikloke/perigee/pull/56
- Source: `76939d3ea69a6ce71a3a6242f4adfea48fed583e`
- Cloudflare Worker version: `e2a201b3-a0df-4c90-bce4-2ce45f8107b5`
- Release digest: `02d27fcf4af95daf78d3e12dede50915ec64d3f914d9d3e7f980dfbfb474f892`
- Frontend: 215 tests passed; backend CI: 429 passed, 33 raw-data-dependent tests skipped; Cloudflare parity: 16 passed; Worker: 24 passed. Registration controls: 10 passed, 6 data-dependent skips.
- Public static/edge checks: 28/28 passed; public release identity and every static resource checked match the merged build.
- Public mobile 390px: no horizontal overflow; current cartoon WebP loads. Live rocket replay crosses left with separate animated exhaust. Failed-preset recovery returns to and focuses Choose an investigation.
- Local 1280×800 and 390px: guided-step progress, notebook/reference reveal, Escape, replay and pause/resume checked. No errors/warnings in that normal local journey. Reduced motion covered by lifecycle tests; no OS preference walkthrough or physical-device frame-rate measurement.
- Public live API: release smoke 27/29 on three runs. Nonpreset Orion search returned 502 UPSTREAM_UNAVAILABLE; frame check skipped because there was no search result. Direct Python-origin probe also timed out querying both SPHEREx collections. Investigation data remained available. This is a real remaining live-search limitation, not a passed check.

Screenshots: `published-desktop.png`, `published-mobile.png`; intro sample: `rocket-preview.png`.
Script/captions/shot list: `docs/presentation/SUBMISSION_VIDEO.md` and `perigee-29s-captions.srt`.
Recording, hosting the final video and successful Submit for Judging remain to be completed. Deadline: 15 November 2026 at 11:59 p.m. Chicago local time.

Diagnosis: a matching direct IRSA DR1 SIA request returned a valid response after 21.1 seconds; the Python API read timeout is 20 seconds inside a 25-second overall budget. These probes indicate slow/intermittent archive responses. They do not establish that every request fails. No backend change was made in this release.
