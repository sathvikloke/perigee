# 23 — Regression checks for chosen implementation

Original integration contact: Aditya / integration. Start condition: **after candidate selection**.
Suggested branch: `codex/parallel-23-regression`.
Owned candidate paths: qa/regression/**; focused tests in existing owned test folders.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Re-run the exact reproductions for confirmed defects on the selected integration build. Check nearby behavior when a fix could affect it. Reuse working test infrastructure and maintain a small risk-based suite rather than generating dozens of mirrored tests.

## Required completion evidence

A tested commit, clear pass/fail results and any remaining blocker. Do not run an expensive load test against NASA services.
