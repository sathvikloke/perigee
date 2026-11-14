# 04 — API B: independent robust candidate

Original integration contact: Aditya. Start condition: **after task 03 first interface**.
Suggested branch: `codex/parallel-04-api-b`.
Owned candidate paths: Same API-owned files as task 03, only in your isolated candidate branch.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Implement an alternative of the same bounded API with particular attention to request budgets, partial collection failures, signed-token verification and predictable error types. Preserve every public route and field. Do not introduce a job queue, database or different framework.

## Required completion evidence

Replay the same inputs as candidate A, including malformed token, upstream timeout and partial results. Provide a compact evidence-based comparison; do not claim an improvement without measuring it.
