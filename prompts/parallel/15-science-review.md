# 15 — Independent scientific acceptance

Original integration contact: Sathvik. Start condition: **after processor output**.
Suggested branch: `codex/parallel-15-science-review`.
Owned candidate paths: science/reviews/acceptance/**.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Audit representative outputs from the selected processor against original bytes. Check sky registration, wavelength location, observation time, flags, absent coverage, display stretch and provenance. Use controls independent of the implementation where possible. Existing science/check_frames.py is a useful input, not automatic proof.

## Required completion evidence

A short pass/fail/unknown matrix tied to exact frames and versions. Escalate scientific meaning errors before cosmetic or performance work.
