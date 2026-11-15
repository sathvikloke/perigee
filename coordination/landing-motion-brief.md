# Landing spacecraft refinement

Branch: `codex/landing-satellite-motion`, based on `bb65efa`. Isolated from the coordinator’s release worktree.

## Final direction

A realistic, reference-informed SPHEREx illustration sits beside the desktop headline and below the primary action on phones. Preserve black, electric citron, Host Grotesk, the existing orbital mark, and calm investigation views. The user rejected the initial procedural Three.js model as synthetic; that model and the Three.js dependency are removed.

The replacement is a fixed-view AI illustration, not a rotatable model, mission photograph, live orbit, or scientific observation. Local WebP artwork is 285 KB. A 2.8-second approach settles into a restrained 14-second drift using Web Animations transforms. The entrance never blocks the action. Skip, replay and shared pause controls are available; reduced motion is static. Visibility observers pause offscreen/hidden work, and unmount cancels animations. No new runtime dependency.

## Integration scope

Home.tsx owns the simpler copy, removal of duplicate hero wordmark/captions/secondary link, and a single start action. Landing investigation cards use authored case references so preview pairs match the initial investigation: Barnard A+C, Epsilon A+B, WISE A+B. Explicit target/question button labels improve navigation. The lower action says Search archive and mentions object names and coordinates, matching the coordinator’s upcoming search changes.

Styles are isolated in landing-motion.css, imported after orbital.css. OrbitField accepts optional external pause and hidden-control props. No investigation, API, notebook, routing, metadata, or deployment work is included. The coordinator owns those areas.

## Review and provenance

The user’s Obsidian 3D research reinforced choosing representation for the actual interaction and replacing a weak asset before adding effects. A fixed approach and drift does not require a complete 3D mesh; a future user-controlled orbit would. NASA hardware references, generation details and limitations are recorded in [ASSET.md](../qa/landing-motion/ASSET.md). Verification and visual evidence are in [VERIFICATION.md](../qa/landing-motion/VERIFICATION.md).

The broader 50-winner comparison is a separate deliverable in the science workspace’s audit/winners-2021-2025 directory. This commit does not deploy the app.
