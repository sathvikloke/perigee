# Claude execution coordinator: Perigee

Sathvik explicitly authorizes you to dispatch parallel implementation attempts across all six original roles, including duplicate attempts at the same task. The goal is a working two-day hackathon product. Codex owns UI design and is preparing the visual direction in this repository. You own implementation dispatch and candidate integration, not a new design direction.

Read `prompts/parallel/README.md`, its task files, `docs/INTEGRATION_CONTRACT.md`, and `docs/SPRINT_BRIEF.md`. Start execution immediately. Do not spend the turn rewriting the plan or reading six 18,000-word prompts. Use the long prompts only to resolve a concrete question.

## Dispatch

Keep roughly five productive implementation agents active, each in a separate Git worktree and branch. Queue the remaining tasks by prerequisites; queueing is not a claim that they are running. Start API A, processor A, catalog/assets, deployment preparation, and one frontend implementation. Frontend work can establish behavior against the contract while Codex supplies the design artifact; it must preserve Codex's chosen visual direction once available. Run competing frontend/API/processor candidates when capacity permits, then compare concrete results rather than merging both implementations.

Use native Claude subagents with worktree isolation if available. If cross-session tools are available, separate Code sessions are also appropriate. Record actual task IDs, worktree paths, branches, statuses, outputs and blockers in `coordination/claude-dispatch.md`. Do not claim agents were launched merely because you wrote task descriptions. If agent tools are unavailable, report that concrete limitation and execute the highest-priority independent task yourself.

There is an existing Claude session titled “NASA Space Apps overview” doing Sathvik's science/content work in the original checkout. Preserve its uncommitted `science/**` and `backend/content/**` files. Do not switch its branch, reset it, stage its files, or rewrite them. Use completed content via an intentional commit or read-only handoff. Do not start duplicate case authoring ahead of blocked implementation unless an independent check is useful.

## Integration

Create a dedicated integration worktree. Workers commit and may push only their candidate branches; they do not push main, promote production, rename shared models or change the architecture independently. Compare duplicate candidates on the same public contract, real-data path, correctness and ease of integration. Choose one coherent base and selectively bring over genuinely useful changes. Avoid combining two competing scaffolds, lockfiles or routing models.

You may assemble and test the selected implementation on an integration branch and open a pull request. Preserve the original owners as review contacts. Keep the public main branch stable; report the integration PR and test evidence to Sathvik. Do not create another Vercel production project, change production secrets, or alter access controls as a side effect of a duplicate deployment experiment. Use previews and existing authorized configuration.

## UI direction

Every task touching visible UI must actually read and apply `/Users/sathvikloke/.codex/skills/bloody-coconut-design/SKILL.md` and the relevant playbooks it dispatches, including installed Impeccable. The user explicitly requested this. Codex is reading the Obsidian UI vault and owns `design/**`, PRODUCT.md and the selected visual direction. Follow `design/HANDOFF.md` when it appears. Do not independently replace its composition, type, palette or interaction meaning. If the skill cannot be accessed, record the missing path and continue nonvisual work; do not claim it ran.

## Keep moving

Seek the first real observation → API → viewer → evidence export within two hours of implementation start, then the non-preset live query. Deliver a concrete first artifact within about 30 minutes per worker. When blocked for 20 minutes, record the exact missing input and reallocate to useful work. No runtime AI feature, new database, full spectra, precision photometry, accounts or third investigation belongs on the critical path.

Only Sathvik and Sagar need the full NASA data. Agents running here on Sathvik's laptop may read retained originals under `/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data` without copying the archive into every worktree. Keep raw data and credentials out of Git. Never recover deleted starter implementation from Trash. Build new code from retained original observations and public documentation.

Finish each work packet with the branch, changed paths, reproducible command, observed result and remaining limitation. A mock result is not a NASA result, a README is not a deployment, and a READY deployment label is not proof that the complete application works.
