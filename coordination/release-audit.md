# Release completion audit (post-release, 2026-11-15)

**Release under audit:**
- **App code:** `main` @ `ef298900aa5769c47ec32f2bdb7c94ac27af14f3` (PR #27). This is the release candidate `54137e0`; the code is identical to `2956e67`.
- **Production:** `https://perigee-liard.vercel.app`, deployment `dpl_4gggyXwZGgMaUtSPRUSJx6iJUMjq`, public.
- **Docs:** Codex's PR #37 (`c02adab`) is docs only and changes no app code.
- **Owners:** Codex owns the release, deployment, root README, `docs/DEPLOYMENT.md` and `qa/public-release/`. This file and `qa/production-journey/` are the coordinator's.

**Legend:**
- **Done:** completed, with evidence.
- **Superseded:** a competing candidate, not selected (kept for the record, not to be reopened).
- **Fix needed:** a verified defect.
- **Blocked (external/user):** needs a person or an external party.

## 1. The 24 parallel tasks

| ID | Task | Status | Evidence |
|---|---|---|---|
| 01 | Frontend A | **Done** (selected) | Integrated; design A; `qa/production-journey/` |
| 02 | Frontend B | **Superseded** | PR #18; first-viewport idea ported into 01 |
| 03 | API A | **Done** (selected) | PR #12; live `/search` and `/frame` on production |
| 04 | API B | **Superseded** | PR #16; body-cap and limiter ideas reviewed in 14 (D2) |
| 05 | Processor A | **Done** (selected, now 0.1.2) | PR #11, #21; `e7c263d`; PR #35 fixes |
| 06 | Processor B | **Superseded** | PR #14 |
| 07 | Vercel deployment | **Done** | Production public; Codex's release smoke run 43658316997 passed |
| 08 | Catalog and assets | **Done** | PR #10; R7 `454d027`; production assets 200 |
| 09 | Epsilon Indi B case | **Done** | Review `a4d2de9` plus revision `b5aff70`, accepted |
| 10 | Barnard case | **Done** | Review `eaa59fe` plus revision `b4fcc8c`, accepted |
| 11 | Five-target identity audit | **Done (review)**; text-only candidate awaits Sathvik | `science/reviews/targets/` (`63ac37d`, cherry-picked from `claude/parallel-11-target-audit` `49f4f8c`). The candidate `487bf8a` is on that branch, not merged. See section 5 |
| 12 | Evidence export | **Done** | PR #30; QA-F1; production export verified |
| 13 | Quality controls | **Done** | PR #33; production flags and flag-screen panel |
| 14 | API review | **Done** | PR #20; R1–R7 fixed; D1–D3 settled (`03bb179`) |
| 15 | Science acceptance | **Done** | PR #15; 189/189; re-run in every gate |
| 16 | Deployed end-to-end | **Done** | `qa/production-journey/README.md` (this round) and Codex's `qa/public-release/` |
| 17 | Mobile and keyboard | **Done** | PR #25; QA-F3 320 px and focus fixes; production at 390 and 320 |
| 18 | Loading and recovery | **Done** | PR #32; production expired-token, stale-response and partial-retry checks |
| 19 | Performance | **Done (recommendation)** | Local processing takes 32 ms per frame; the hosted frame median is 3.67 s. The likely dominant cost is the external IRSA fetch plus hosting overhead. IRSA time was not measured separately. No code change. See `qa/production-journey/README.md` |
| 20 | Pitch and demo | **Done (outline and script)** | `docs/presentation/README.md` and rehearsal assets. **The shareable deck itself is not built** (section 4) |
| 21 | Judging critique | **Done** | PR #24; findings 1–3 addressed (public app, Play over series, README and AI disclosure) |
| 22 | Submission links | **Done for links; submission is the team's** | Section 4: all key links return 200 logged out |
| 23 | Regression | **Done** | PR #26; `qa/regression/run.sh` passing on every merge |
| 24 | Compare and assemble | **Done** | 24c, 24p, 24r, 24f; PR #19 decision (keep A, port the quality rule) |

## 2. App requirements (challenge, sprint gates, integration contract)

| Requirement | Status | Evidence |
|---|---|---|
| Any public RA/Dec reaches the archive, with frames in time order (challenge) | **Done** | Production: 460 matches; 24 frames in time order |
| Gate 1: curated observation → deployed API → viewer → exported card | **Done** | Production journey: export with `data_origin: api` |
| Gate 2: known-covered non-preset coordinate → real frame | **Done** | Production: Orion and Epsilon Indi A searches give real frames |
| Two investigations and five presets; quality, provenance, saved evidence | **Done** | Production journey |
| Input validation: no partial parses, no silent clipping | **Done** | Production: RA `400` / Dec `12abc` send no request; API tests |
| Allowlisted collections; no user-supplied URLs | **Done** | API tests (R4); signed tokens bound to an allowlisted URL |
| `partial` / `empty` / error semantics | **Done** | D1 (`collections_capped`); production partial frames with retry |
| Expired token gives a clear refresh and keeps notes | **Done** | Production contract check (simulated 410) |
| Stale responses ignored after a coordinate change | **Done** | Production contract check: the older search was cancelled |
| A failed frame does not reorder or discard others | **Done** | Production: 3 failed frames kept their slots and retry recovered them |
| No refetch of loaded frames; no duplicate submit storms; 2-frame concurrency | **Done** | Frame cache, `isDuplicateSubmit` and limiter, with unit tests |
| FrameRecord fields, fixed north-up grid, nullable wavelength | **Done** | Contract tests; 189/189 acceptance |
| Shared stretch for curated pairs; per-frame stretch disclosed | **Done** | Production A+B and A+C notes; F4 sentence |
| Marker is always `catalog_prediction` | **Done** | Production label "Catalog prediction, not a detection" |
| Corrupt or truncated FITS gives 422 `UNSUPPORTED_DATA` | **Done** | PR #35 plus an API test (`eaa92f5`) |
| Evidence card (local storage, JSON export, print) | **Done** | Production export and print PDF |
| Shared URL carries coordinates, FOV and case, never notes | **Done** | Production contract check |
| Public access with no login | **Done** | Logged out: `/` 200, health 200 `ok`, `token_signing: env` |
| Rate limiting (`RATE_LIMITED`) | **Not implemented, by decision (D2)** | Per-request bounds only. An optional Vercel Firewall rule is the release owner's call |

## 3. Owner issues #1–#6: evidence mapping (for the tracker; issues untouched)

Each work-sequence item from the issue body maps to released evidence. "**Gap**" marks something genuinely unfinished.

### #1 Sathvik: science, content, integration leadership
| Item | Evidence |
|---|---|
| Establish the current integration state | `coordination/claude-dispatch.md` (coordinator on Sathvik's behalf) |
| Verify target identity and coordinate context | **Done.** Task 11 found all five presets match SIMBAD: names, J2000 positions, proper motion, parallax and RV. Query centers match within 1e-4″ and markers reproduce within 0.0007 px. Two text items await Sathvik (section 5) |
| Select the first comparison case | `fair_comparison` (Epsilon Indi B), from #8 |
| Validate the moving-star investigation | Barnard review `eaa59fe`; revision #22 accepted |
| Author concise case content | Both case JSONs, `science_owner_approved` (`6f08d56`) |
| Review scientific processing outputs | Acceptance 189/189 (#15); PR #19 and #35 reviews |
| Validate the integrated learner journey | Rehearsal (`docs/presentation/`) and production journey |
| Verify the live coordinate requirement | Production live search, 460 matches |
| Build the story and presentation | Outline and script done. **Gap: no shareable deck or ≤30 s video yet** |
| Lead the final integration and release decision | PR #27 merged (`ef29890`); production public |
| **Acceptance** | Met, except "a tested public **submission**", which is the team's final step, plus the deck |

### #2 Sagar: archive and image pipeline
| Item | Evidence |
|---|---|
| Inventory original sources | `research/build_data/manifest.json`; `tools/ingest/fetch_manifest.py` (Sagar, adopted) |
| Define the data adapter interface | `backend/data/process.py` `process_frame(bytes, FrameInput)`; API adapter |
| Implement bounded archive discovery | `backend/routes/_archive.py` (SIA, MAXREC, allowlist) |
| Retrieve and validate small cutouts | `backend/security/upstream.py` (byte caps, retry); PR #35 truncated-FITS handling |
| Build the common celestial grid | 256 px over 6′, north up; Gaia median 0.45 px |
| Calculate wavelength context | WCS-WAVE at the target position; null off-image; audit tolerance (#35) |
| Implement coverage and flag interpretation | Quality screen 0.1.2, with Sagar's unknown rule adopted |
| Create display scaling and PNG outputs | Nearest-neighbour plus asinh; shared case stretch |
| Prepare the two curated investigations | `backend/content/presets/*/case-*` |
| Deliver reproducible data evidence | `tools/ingest/audit_all.py` (183, 0 stale); `diff_products` |
| **Acceptance** | **Met.** Non-preset search to a traceable frame through the backend interface, on production. Note: Sagar's own processor (#19) was trial-integrated, not selected; his fetch, registration-check and quality-rule work ships |

### #3 Akshobya: frontend
| Item | Evidence |
|---|---|
| Foundation, first investigation screen, coordinate exploration | Frontend A plus design A; production |
| Progressive chronological loading | Production: 24 frames in time order, 2-frame concurrency |
| Separate time from wavelength | A+B versus A+C notes; "Near X µm" filter (#33) |
| Quality without a fake score | Four quality states, flag panel; no score |
| Guided case flow | Steps, hints, claim guide |
| Evidence saving and export | Autosave, JSON export, print, My evidence and Reopen |
| Responsive and accessible | 390 and 320 px; focus management; axe 0 violations (PR #25) |
| Integrate and hand off | Merged in PR #27 |
| **Acceptance** | **Met** (production journey). Built by Claude workers in place of the named owner, who had a pending invitation; the tracker should say who reviewed it |

### #4 Aditya: API
| Item | Evidence |
|---|---|
| Typed models, entry point, coordinate validation | `backend/models/**`, `backend/main.py`, API tests |
| Archive metadata search, frame tokens, frame orchestration | `/search`, HMAC tokens, `/frame`; production |
| Consistent failure semantics | Error envelope; R1–R7; D1; 422 for corrupt FITS |
| Bound work, avoid duplicate storms | Budgets, byte caps, retry bounds; frontend limiter and duplicate guard |
| Verify serverless behavior | Production health `ok`; release smoke passed; D3 local-only dev secret |
| Publish the API handoff | `docs/INTEGRATION_CONTRACT.md` (updated for D1); `backend/tests/api/REVIEW.md` |
| **Acceptance** | **Met.** No global rate limiter, by decision D2 |

### #5 Suhrit: platform and deployment
| Item | Evidence |
|---|---|
| Verify the Vercel target; Services deployment path | `vercel.json` Services; production public |
| Content catalog serving; safe asset serving | Catalog routes; traversal-safe, hash-checked assets; R7 |
| Optional cache adapters | **Not built (optional).** Hashed assets are served immutable, the live path is stateless, and no need was measured |
| Environment configuration | `PERIGEE_TOKEN_SECRET`, set by Codex for Production and Preview; dev secret refused on hosted |
| Control bundle and runtime size | `.vercelignore`; `deploy_check`; JS 327,624 B uncompressed (105,250 B Brotli transfer, 102,051 B gzip) |
| Deployment verification | `backend/platform/smoke.py` (#34, hardened); `release-smoke.yml` (#36); run 43658316997 passed |
| Production release behavior; operations and recovery handoff | `docs/DEPLOYMENT.md` (Codex's current-release rewrite, PR #37) |
| **Acceptance** | **Met.** Public deployment, curated assets resolve, no team login. The automatic `deployment_status` trigger is still unverified, as documented; the manual run passed |

### #6 Neeraj: QA
| Item | Evidence |
|---|---|
| Minimum: verify public access | Pre-release blocked, recorded in issue #6. Now public: verified by Codex and in this audit |
| Minimum: complete one investigation | `qa/fresh-pass` (local, `cc2c3ca`); production journey |
| Minimum: check submission links | Neeraj's 31-link check (pre-release). Post-release key links all return 200 (section 4) |
| Optional: narrow screen, keyboard, error states, save and revisit, demo support, regression | Covered by QA-F3, rehearsal, the production journey and contract checks (not by Neeraj) |
| Finish with a compact QA handoff | Neeraj's issue #6 comment; findings F1–F4 all fixed |
| **Acceptance** | **Minimum met by Neeraj, pre-release.** A re-run on the public URL is optional (his own note) |

## 4. Submission readiness (task 22). Nothing was submitted.

Official rules, from the project submission guide read on 2026-11-14:
- the demo is a ≤7-slide deck (including title and intro slides) or a ≤30 s video, at a **public link**;
- the final-project link is public;
- the deadline is Sunday 15 Nov, 11:59 p.m. Local Event time.

**Links checked logged out on 2026-11-15, all HTTP 200:**
- the app and `/api/v1/health`;
- `github.com/sathvikloke/perigee` and `…/blob/main/docs/AI_USE.md`;
- the challenge page;
- IRSA SPHEREx, the IRSA tutorial and the archive-access docs;
- SIMBAD (CfA mirror), Epsilon Indi B and Barnard's Star;
- Gaia and Gaia DR3.

**Genuinely missing before submission (team or user actions):**
1. **The demo deck itself.** Only a 7-slide *outline*, a script and screenshots exist (`docs/presentation/`). Nobody has built a shareable deck (or a ≤30 s video) or hosted it at a public link. It must show the team name, members and challenge.
2. **`docs/AI_USE.md` `[TO CONFIRM]` items: 7 open**, all team attestations:
   - the image tool for mocks;
   - planning-doc tooling;
   - Sagar's AI use;
   - AI use outside the repo;
   - who reviewed which merges;
   - **the idea's origin**, which the guide requires to be the team's own;
   - human spot checks.
   Agents must not fill these.
3. **Project page text:** the description, the data/resources list and the "Use of SI" answer, written in the Space Apps form by the submission owner. The README and `docs/AI_USE.md` provide source material.
4. **The "Submit for Judging" click**, before the deadline. This is the team's action.
5. **The local presentation slot**, to be confirmed with the Local Lead. No official local talk length was found.

## 5. Remaining gaps and notes
- **Fix needed: none found.** The production journey and contract checks surfaced no application defect.
- **Task 11 (five-target identity audit): done; no coordinate value changes.** Review in `science/reviews/targets/README.md`, with raw source snapshots and scripts. Findings needing a science-owner decision, held as **candidate `487bf8a`** on `claude/parallel-11-target-audit` (`backend/content/targets.json` only, text only; no product rebuild; backend tests 330 passed / 18 skipped):
  1. **Mislabeled source.** WISE 0855 `astrometry_reference` says "CatWISE2020 (2021ApJS..253....7K)". That bibcode is Kirkpatrick et al. 2021, the 20 pc census; CatWISE2020 is 2021ApJS..253....8M. The label also appears in the 34 shipped WISE 0855 records' `marker.source` until a future rebuild.
  2. **New field-star note.** Gaia DR3 5756956644387831296 (G 16.3) lies 4.5–11.8″ from the WISE 0855 marker in shipped frames, and about 3.2″ around 2026.73. A spot near the marker is likely that star, not WISE 0855. The candidate adds one sentence to the WISE 0855 `quality_summary`.
  - **No change recommended:**
    - Eps Ind B sits 0.56 ± 0.07 display px from the marker, consistent across 32 frames. Gaia's proper-motion fit is poor (RUWE 4.30) because Ba/Bb is an unresolved binary. That is 0.13 native px, and no quality screen changes.
    - The Barnard's Star radial-velocity epoch convention moves the marker 0.27 px.
    - RW Aur is an A/B blend, offset 0.56 px.
    - R Dra's missing RV has an effect under 1e-5 px.
    - The WISE 0855 challenge coordinate matches its catalog track at 2010.45.
  - **Limitations:** centroids are a consistency check (6.1″ native pixels, crude centroid). The Ba/Bb orbit was not modeled. WISE 0855's own detectability was not tested.
- **Optional, release owner:** immutable caching for hashed `/assets/*`; a Vercel Firewall rate-limit rule.
- **Not covered by anyone:** a physical phone, a screen reader, the native print dialog, browsers other than Chrome.
