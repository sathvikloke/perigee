# 19 — Measure and fix the slowest real path

Original integration contact: Suhrit / Sagar. Start condition: **after a deployed real-data path**.
Suggested branch: `codex/parallel-19-performance`.
Owned candidate paths: qa/performance/**; one focused candidate performance patch.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Measure a representative deployed search and frame conversion: cold/warm duration, upstream time, bundle and response size, and relevant browser work. Identify the dominant delay before changing code. Bound image dimensions and avoid unnecessary repeated downloads while preserving provenance and correctness.

## Required completion evidence

Before/after measurements for one substantive improvement, or an evidence-based recommendation if the delay is external. No broad optimization framework or unmeasured speed claim.
