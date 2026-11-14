# 24 — Compare duplicates and assemble the best candidate

Original integration contact: Integration coordinator. Start condition: **after first competing results**.
Suggested branch: `codex/parallel-24-integration-compare`.
Owned candidate paths: coordination/**; integration branch only.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Execute this task

Compare competing frontend, API and processing branches on identical contract examples and the same real-data acceptance path. Choose one base per component, then selectively integrate useful differences. Resolve schema and dependency conflicts explicitly. Preserve the Codex design and existing science work.

## Required completion evidence

One integration branch/PR with a coherent working flow, a brief explanation of selected candidates and reproducible checks. Do not merge two scaffolds wholesale or push broken experiments to main.
