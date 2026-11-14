# 03 — API A: live coordinate and frame path

Original integration contact: Aditya. Start condition: **now**.
Suggested branch: `codex/parallel-03-api-a`.
Owned candidate paths: backend/main.py; backend/models/**; backend/routes/search.py; backend/routes/frames.py; backend/routes/health.py; backend/security/**; backend/tests/api/**.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Implement FastAPI models and the bounded search/frame routes from the contract. Separate archive orchestration from Sagar's processor. Validate finite RA/Dec, field size and result limit; sign frame descriptors and map upstream failure separately from successful empty results. Provide actual example payloads to frontend and catalog owners immediately.

## Required completion evidence

Exercise a known-covered non-preset coordinate and one real frame when the adapter exists. Until then, verify protocol tests with clearly labeled fixtures and name the exact integration dependency.
