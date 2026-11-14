# 08 — Serve cases, presets and small assets

Original integration contact: Suhrit. Start condition: **now**.
Suggested branch: `codex/parallel-08-catalog-assets`.
Owned candidate paths: backend/routes/catalog.py; backend/platform/catalog*; backend/tests/platform/**.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Implement catalog and allowlisted asset routes from the contract. Consume actual case/target content from the science owner and generated frame records from the processor. Preserve scientific meaning and return honest missing-content states. Prevent arbitrary filesystem paths and do not bundle the raw archive.

## Required completion evidence

Five preset descriptors serialize consistently; one real case and frame asset reach the browser with correct media types and source IDs. Missing files return a clear API response.
