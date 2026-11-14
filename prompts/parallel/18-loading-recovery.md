# 18 — Loading, partial results and recovery

Original integration contact: Akshobya / Aditya. Start condition: **after selected frontend and API**.
Suggested branch: `codex/parallel-18-loading-recovery`.
Owned candidate paths: frontend request-state/recovery modules; contract-compatible candidate fixes.

You are a Claude Code worker for Perigee, a two-day NASA Space Apps web app. Sathvik explicitly authorized parallel attempts across teammates' original assignments, including duplicates. Work only in your isolated Git worktree and candidate branch. Never switch, reset, stage or overwrite another session's checkout. Existing uncommitted science/content work belongs to the original Claude session and must be preserved.

Read docs/SPRINT_BRIEF.md and docs/INTEGRATION_CONTRACT.md first. Spend at most ten minutes orienting, then produce a concrete first artifact. React/TypeScript/Vite frontend, FastAPI/Astropy backend, Vercel hosting; keep the public contract stable. No runtime AI, account system, database, precision-photometry claim or broad redesign. Only Sathvik and Sagar need the full archive; local data workers may read the original dataset on Sathvik's laptop without copying it into every worktree. Missing fixtures and mocked results must remain explicit.

Commit only your work. You may push your candidate branch and open a focused PR, but do not push main or promote production. Hand off branch/commit, changed paths, exact commands, observed results and limitations. If blocked for 20 minutes, report the precise missing dependency and perform useful independent work. A review task produces a factual review; an implementation task must continue beyond a plan. Do not send external emails or alter unrelated services.

## Required design workflow

Read and actually use `/Users/sathvikloke/.codex/skills/bloody-coconut-design/SKILL.md`, including relevant installed Impeccable playbooks. Follow Codex's `design/HANDOFF.md` and selected design artifact when available. Codex owns visual direction. Before it lands, build semantic behavior and API wiring without committing a replacement aesthetic. Do not add invented NASA imagery or generic space decoration as scientific evidence. If this local skill is inaccessible, state the exact gap and continue nonvisual work; do not claim it ran.

## Execute this task

Implement and verify coherent metadata-loading, per-frame loading, partial, empty, expired-token and upstream-failure states. Ignore stale query responses and preserve notes through failures. Use AbortController or equivalent cancellation where useful, bounded browser concurrency and explicit retry actions.

## Required completion evidence

Reproduce a slow old response, one failed frame and a storage-preserving retry. Show that neither result ordering nor the learner's written work is corrupted.
