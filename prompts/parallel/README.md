# Parallel Claude task pack

24 concrete worker prompts plus one coordinator. The user authorizes alternate implementations across original role boundaries. Original owners remain integration contacts. **Codex owns UI design; Claude owns the implementation candidates.**

Start the [coordinator](COORDINATOR.md), which queues all 24 tasks and starts about five productive workers at a time. Initial wave: 01, 03, 05, 07, 08. Existing science work continues in its original session. Duplicate candidates 02, 04 and 06 are intentional; compare them and select one base rather than merging both wholesale.

Each worker needs its own worktree. Claude Code supports `claude --worktree <name>` and a Desktop worktree option ([official documentation](https://code.claude.com/docs/en/worktrees)). For manually created branches, use `codex/parallel-<id>-<task>`. Uncommitted files and ignored raw data do not automatically appear in fresh worktrees. Use intentional read-only handoffs or committed inputs; never reset the original checkout to make a candidate fit.

Paste into an isolated Claude Code session:

> Read `prompts/parallel/NN-TASK.md` and execute it. Inspect the current repository first, preserve other sessions' work, and return a verified candidate with a precise handoff.

| ID | Task | Original contact | Start condition |
|---|---|---|---|
| 01 | [Frontend A: complete investigation flow](01-frontend-a.md) | Akshobya | now |
| 02 | [Frontend B: competing implementation](02-frontend-b.md) | Akshobya | after design handoff |
| 03 | [API A: live coordinate and frame path](03-api-a.md) | Aditya | now |
| 04 | [API B: independent robust candidate](04-api-b.md) | Aditya | after task 03 first interface |
| 05 | [Processor A: one original FITS to browser frame](05-processor-a.md) | Sagar | now |
| 06 | [Processor B: independent processing candidate](06-processor-b.md) | Sagar | after one representative source is selected |
| 07 | [Vercel frontend and Python integration](07-deployment.md) | Suhrit | now |
| 08 | [Serve cases, presets and small assets](08-catalog-assets.md) | Suhrit | now |
| 09 | [Epsilon Indi B case review and improvement](09-epsilon-case.md) | Sathvik | after existing science handoff |
| 10 | [Barnard moving-star case review](10-barnard-case.md) | Sathvik | after existing science handoff |
| 11 | [Five-target identity and coordinate audit](11-target-audit.md) | Sathvik | now; review existing work read-only first |
| 12 | [Evidence card persistence and export](12-evidence-export.md) | Akshobya | after selected frontend scaffold |
| 13 | [Wavelength, quality and comparison controls](13-quality-controls.md) | Akshobya | after selected viewer scaffold |
| 14 | [API reliability and security review](14-api-review.md) | Aditya | after API candidate |
| 15 | [Independent scientific acceptance](15-science-review.md) | Sathvik | after processor output |
| 16 | [Deployed end-to-end integration check](16-end-to-end.md) | Neeraj / integration | after running app |
| 17 | [Mobile and keyboard repair](17-mobile-accessibility.md) | Akshobya / Neeraj | after selected frontend |
| 18 | [Loading, partial results and recovery](18-loading-recovery.md) | Akshobya / Aditya | after selected frontend and API |
| 19 | [Measure and fix the slowest real path](19-performance.md) | Suhrit / Sagar | after a deployed real-data path |
| 20 | [Human story and demonstration script](20-pitch.md) | Sathvik | now for outline; update from actual build |
| 21 | [Independent judging critique](21-judge-review.md) | Sathvik | after one demonstrable flow |
| 22 | [Submission links and attribution check](22-submission.md) | Sagar / Neeraj | after candidate release |
| 23 | [Regression checks for chosen implementation](23-regression.md) | Aditya / integration | after candidate selection |
| 24 | [Compare duplicates and assemble the best candidate](24-integration-compare.md) | Integration coordinator | after first competing results |

No extra work is required merely because it appears in this pack. The coordinator starts dependency-ready tasks, records actual execution status and stops optional work when the core needs attention. Every frontend-related worker must apply Bloody Coconut and preserve Codex's chosen design. Prompts 02/04/06 deliberately duplicate implementation; 09–11 independently review science already underway instead of overwriting it.
