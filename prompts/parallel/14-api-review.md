# 14 — API reliability and security review

Original integration contact: Aditya. Start condition: **after API candidate**.
Suggested branch: `codex/parallel-14-api-review`.
Owned candidate paths: backend/tests/api/**; focused candidate API fixes.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Review the current API against actual failure risks: finite coordinate validation, signed token tampering/expiry, arbitrary upstream URLs, redirects, payload budgets, bounded retries and partial-result semantics. Write only checks that catch a consequential behavior. Fix the smallest confirmed defect in your candidate branch.

## Required completion evidence

A ranked finding list with reproductions and focused patches. Do not claim a comprehensive security certification or add speculative infrastructure.
