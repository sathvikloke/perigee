# 05 — Processor A: one original FITS to browser frame

Original integration contact: Sagar. Start condition: **now**.
Suggested branch: `codex/parallel-05-processor-a`.
Owned candidate paths: backend/data/**; backend/tests/data/**; tools/ingest/**.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Implement the smallest new FITS processing path from retained original bytes. Inspect actual extensions and headers. Produce a fixed-grid PNG, observation metadata, target-position wavelength, meaningful coverage/quality state and source provenance. Keep network retrieval separate from pure image conversion. Hand one real FrameRecord to the API team early.

## Required completion evidence

Inspect one result against its original FITS and metadata. Preserve unknown values, label predicted markers correctly and never equate a clean flag screen with a detection.
