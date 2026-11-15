# Hero return and submission materials — 15 November 2026

- Fixed one-shot hero/satellite entrances retaining partial opacity or masks on viewport departure. Returning shows static visible content; ambient drift resumes. Explicit replay remains available.
- Regression suite: 227 frontend tests passed; production build passed. Cloudflare parity: 16 passed; Worker: 24 passed.
- Local browser scroll away/return: headline opacity 1, clip-path none, arrival false; satellite and CTA visible, no horizontal overflow at observed 718px viewport. A requested 390px browser override did not change this tab, so this is not claimed as a 390px walkthrough.
- Expanded exactly seven slides, reviewed each render. Avenir Next typography; observation images unchanged. Replaced obsolete screenshot, separated captions, repaired the processing-column overflow and lower-slide overlap. Full name Aditya Raut used.
- Editable deck: https://chatgpt.com/space/page_c2bdc1167fb481918cc92fabeb2bfc58
- Public PDF packages reviewed live renders; native PDF export could not embed the local font. Selectable transcript: docs/presentation/DECK.md. The Spaces deck remains editable.
- Technical report: exactly eight pages; source, build and visual checks under docs/report.
- Live archive reliability is unchanged by this frontend/document release. Earlier bounded probes and API failures are recorded in qa/landing-motion/RELEASE.md.

Release identity and published verification follow in release.json after deployment.
