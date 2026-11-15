# SPHEREx-inspired landing artwork

Created 15 November 2026 with OpenAI’s built-in image generation tool, directed by Codex in response to the user’s explicit request for more realistic spacecraft artwork.

- Original transparent 1280×1280 output: `artwork-source.png`.
- Served local asset: `frontend/public/illustrations/spherex-observatory.webp`, approximately 285 KB, converted with Sharp.
- Visible app caption: “SPHEREx | AI illustration”.
- No generated imagery is used as an observation or scientific evidence. This is an artistic interpretation, not an engineering-accurate mesh, photograph, or live mission position.

## NASA reference material

Both hardware photographs were viewed before generation and supplied as visual references:

- [JPL SPHEREx spacecraft press kit](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/), describing nested photon shields, telescope, spacecraft bus and solar panel.
- [Outer shield installed](https://d2pn8kiwq2w21t.cloudfront.net/images/SPHEREx_Outer_Shield_Installed.width-640.jpg), locally `references/spherex-hardware.jpg`, NASA/JPL-Caltech/BAE Systems.
- [Telescope testing](https://d2pn8kiwq2w21t.cloudfront.net/images/SPHEREx_Testing.width-640.jpg), locally `references/spherex-telescope.jpg`, NASA/JPL-Caltech.

## Generation direction

The prompt requested an exceptionally realistic isolated SPHEREx-inspired spacecraft on a transparent background, using the photographs for structural proportions and material cues. An elevated three-quarter view shows three thin nested shields, white aerospace aluminum with seams and fasteners, silver thermal foil, fine support struts, a dark rectangular baffled telescope aperture, a compact bus with brackets/cabling/crinkled gold and silver insulation, and one dark navy rectangular solar array with dense photovoltaic cells. Lighting is a cool white key from upper left with restrained fill and dark neutral shadows.

It explicitly excluded laboratory surroundings, people, supports, flags, loose ground cables, logos, text, Earth, stars, glow, exhaust, emitted beams, cartoon features, thick plastic bowls, clay shading, and low-poly geometry. The prompt specified a transparent margin, credible hardware detail, and artistic rather than diagrammatic status. The generated result was inspected before integration; it was not reconstructed as a mesh.

## User-vault references used

Read-only notes in `/Users/sathvikloke/Documents/Codex/2026-11-13/rand/outputs/3d-design-research/vault`:

- `12 - 3D Production/01 - Choose the rendering method.md`
- `12 - 3D Production/03 - Asset fidelity is a dependency.md`
- `12 - 3D Production/05 - Lighting and material coherence.md`
- `03 - Prompt Library/32 - Replace a synthetic hero asset.md`
- `03 - Prompt Library/34 - Repair lighting and material realism.md`

Applied principle: the asset carries close-up realism; a fixed-view presentation can use image motion, while orbit or changing lighting would need a complete authored model. Do not add bloom to conceal geometry or material weaknesses.
