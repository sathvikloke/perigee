# Claude dispatch log — Perigee parallel implementation

Coordinator + integration worktree: `.claude/worktrees/perigee-parallel-coord-4aa087`, now on branch `claude/perigee-integration` (from `origin/main` @ `fa92766`). The harness forbids this session from writing into other worktrees, so the coordinator's own worktree is the dedicated integration worktree.
Source of task pack: `prompts/parallel/` on `origin/main` @ `fa92766`.

Only rows marked **running** have an actually launched agent. "Queued" means not started.

## Launch mechanism

Native Claude Code subagents (`Agent` tool, `general-purpose`, `isolation: worktree`, background). Each has its own git worktree under `.claude/worktrees/agent-<id>`, created from `fa92766` (verified with `git worktree list` at 17:38Z). Each worker is instructed to `git checkout -b codex/parallel-NN-<task>` and push only that branch. `worktree-agent-<id>` is the harness default branch before the worker renames it.

## Shared seams set by the coordinator (in every brief)

- Backend package `backend/`; `backend/main.py` exposes `app`; route modules export `router = APIRouter()` with paths relative to `/api/v1`, mounted with `prefix="/api/v1"`. 03 owns main/models/requirements; 08 delivers `backend/routes/catalog.py` router only; integration wires it.
- Processor seam (05): pure `backend/data/process.py::process_frame(fits_bytes, FrameInput) -> ProcessedFrame` (FrameRecord-shaped dict + PNG bytes); network in `backend/data/archive.py`; ingest CLI in `tools/ingest/`; products in `backend/content/presets/<preset_id>/`.
- Frontend (01): `frontend/`, one API client `frontend/src/api/client.ts`, same-origin `/api/v1`, visibly labeled dev fixtures, neutral replaceable token layer until Codex's `design/HANDOFF.md`.
- 07 may push tiny files labeled "DEPLOYMENT PLACEHOLDER" to prove a preview; those never enter integration.
- Science: PR #8 (`origin/codex/sathvik-science`) used read-only via `git show`; 08 imports `backend/content/targets.json` + `cases/` in a separate attributed commit. Binding decisions: `science/INTEGRATION_BOARD.md` (frame_key, DATE-AVG/MJD-AVG, quality rules, null wavelength off-image, fixed grid). The original checkout (science session) is never touched.
- Gate-2 known-covered non-preset coordinate: Eps Ind A, RA 330.8400, Dec −56.7860.
- Raw data read-only at `NASA Space Comp/research/build_data/` (738 MB, 183 FITS); never committed.
- Frontend workers must read/apply `/Users/sathvikloke/.codex/skills/bloody-coconut-design/SKILL.md` (present, verified 17:38Z) + Impeccable. Codex owns `design/**`, PRODUCT.md and visual direction. `design/HANDOFF.md` not present as of 17:38Z.
- Local toolchain: python 3.9.6 only (workers install uv → Python 3.12), node 26, no Vercel CLI auth.

## Wave 1 — launched 2026-11-14 17:38Z

| ID | Task | Status | Worktree | Target branch | Output / blockers |
|---|---|---|---|---|---|
| 03 | API A: live coordinate and frame path | **running** | `.claude/worktrees/agent-aa1e6a902a4de7062` | `codex/parallel-03-api-a` | — |
| 05 | Processor A: one FITS → browser frame | **running** | `.claude/worktrees/agent-ac9eda3765a9fcaa0` | `codex/parallel-05-processor-a` | — |
| 08 | Catalog, presets, assets | **running** | `.claude/worktrees/agent-aff3329b79a0deb37` | `codex/parallel-08-catalog-assets` | — |
| 07 | Vercel deployment preparation | **running** | `.claude/worktrees/agent-a9da251dd88b21712` | `codex/parallel-07-deployment` | Preview builds only; no local Vercel auth |
| 01 | Frontend A: investigation flow | **running** | `.claude/worktrees/agent-a6fde9ea57d0b21dd` | `codex/parallel-01-frontend-a` | Visuals wait for Codex `design/HANDOFF.md` |

## Queue (by prerequisite; not running)

| ID | Task | Prerequisite | Planned slot |
|---|---|---|---|
| 06 | Processor B (duplicate) | 05 first real FrameRecord (representative source selected) | first free slot |
| 04 | API B (duplicate) | 03 first interface/models pushed | first free slot |
| 02 | Frontend B (duplicate) | Codex `design/HANDOFF.md` | when handoff lands |
| 24 | Compare duplicates + assemble | first competing results | coordinator, on this branch |
| 15 | Science acceptance | 05 six-frame output table | after 05 |
| 14 | API reliability/security review | selected API | after 24 |
| 09, 10 | Case reviews | processor products + PR #8 | after 05/06 |
| 12, 13, 17, 18 | Frontend follow-ups | selected frontend (+API for 18) | after 24 |
| 11, 20 | Target audit, pitch outline | none | low priority |
| 16, 19, 21, 22, 23 | E2E, perf, judge, submission, regression | running deployed app | later |

## Integration log

- 17:38Z `claude/perigee-integration` created at `fa92766`. Nothing merged yet.
