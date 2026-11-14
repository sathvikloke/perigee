# Start building: two-day sprint

This brief sets execution priority above the long prompt's reference material. Spend at most ten minutes orienting to your role and the integration contract, then implement. Consult deeper research and scenarios when a concrete implementation question needs them. Do not restart research, redesign the architecture, or turn the reference scenarios into a large test backlog.

## First handoff from each owner

| Owner | Deliver first | Hand it to |
|---|---|---|
| Sathvik | One Epsilon Indi B case: verified source IDs, question, three short steps and supported conclusion | Sagar, Akshobya and Suhrit |
| Sagar | One original FITS converted by new code into a traceable PNG and FrameRecord | Aditya and Suhrit |
| Akshobya | One screen that loads a real frame, shows date/wavelength/quality and saves a short evidence card | Whole team |
| Aditya | Running FastAPI shell, shared response models, health route and bounded search/frame interfaces | Akshobya, Sagar and Suhrit |
| Suhrit | Deployed frontend/API shell, working routing, then one served curated frame and case | Whole team |
| Neeraj | A short fresh-browser pass once the first flow works | Relevant owners |

## Integration targets

These are delivery targets measured from the team's implementation start, not additional time beyond the event deadline. If work has already begun, use actual completed behavior and move directly to the earliest missing gate.

1. **Within two hours:** one real curated observation goes through the deployed API into the viewer and an exported evidence card.
2. **Within four hours:** a known-covered coordinate outside the presets reaches the archive and renders at least one real frame. A graceful error alone does not pass this gate.
3. **Within six hours:** both required investigations and all five presets are wired; quality, provenance and saved evidence work.
4. **Saturday evening:** freeze features, fix blockers and record a backup demonstration.
5. **Sunday morning:** test the public URL, rehearse the pitch and finish the submission artifacts. Confirm the local presentation slot; be ready before it.

Merge small working changes throughout the day. Do not wait for six separate finished branches. If a dependency blocks you for 20 minutes, post the exact missing interface in your issue and continue independent work. A temporary fixture must stay labeled and must not silently replace the real final path.

## Cut immediately when a gate slips

Drop runtime AI, the third investigation, custom design systems, elaborate animation, new infrastructure, accounts and extra research. Defer optional sharing/import conveniences before touching the required coordinate viewer, two investigations, five presets, quality/provenance, one working evidence export and public access. If the four-hour live-query gate fails, Aditya and Sagar resolve that path together while Suhrit checks deployed constraints.

Progress means a demonstrated working flow, not lines of code or completed planning documents. The long master prompts remain available to the coding agents as reference.
