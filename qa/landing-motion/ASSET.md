# Current cartoon landing artwork

Created 15 November 2026 with OpenAI's built-in image generation tool, directed by Codex under the user's explicit cartoon replacement request. The user supplied a cartoon satellite image with a blue/silver palette, dark ink contours and simple cel shading. Its original author or license was not supplied; it informed the requested aesthetic and was not shipped as the app asset.

The generated set contains a generic space telescope, a rocket pointing left, and separate exhaust pointing right. The user requested a white outer contour and clarified that the flame should move independently. OpenAI image-generation edits removed the generated white contour and stray edge flecks; a UI alpha filter supplies the clean white border. This is decorative artwork, not accurate SPHEREx engineering geometry, a photograph, live spacecraft position or observational evidence. The telescope caption reads “Space telescope · AI illustration”; the opening sequence also visibly says “AI illustration.”

## Current assets and conversion

All three final source images and served assets are 1254 × 1254 pixels with alpha. Source PNGs are retained under `qa/landing-motion/cartoon-sources/`, outside the frontend's published assets. Format conversion used Sharp `webp({ lossless: true, effort: 6 })`. Comparing decoded RGBA buffers found zero differing alpha values and zero differing RGB values on pixels with nonzero alpha. No pixel cleanup, geometry synthesis or reillustration occurred during conversion.

| Artwork | Served path under `frontend/public/illustrations/` | PNG bytes | WebP bytes | Reduction |
|---|---|---:|---:|---:|
| Telescope | `perigee-satellite-cartoon.webp` | 918,695 | 551,644 | 40.0% |
| Rocket body | `perigee-rocket-cartoon.webp` | 492,972 | 294,524 | 40.3% |
| Exhaust | `perigee-flame-cartoon.webp` | 322,260 | 188,012 | 41.7% |
| **Total** | | **1,733,927** | **1,034,180** | **40.4%** |

The runtime contour filter thresholds alpha at 0.5 before dilation so faint edge flecks do not become white blobs. It merges the source artwork unchanged over a white silhouette: 14 display pixels for the telescope, 7 for the rocket, and 4 for the flame. The flame is a separate image with its own 190 ms stretch/flicker loop and three trailing embers; it is not a flame painted rigidly onto the rocket.

### Source PNG SHA-256

- Telescope: `66290e00c54bc806e9004aff224285366832ab9366d6e2d46ef7529a6f1e4953`
- Rocket: `673e13abf24db76b184c344290d1d3948638778ccbc85929c84dd8baf8863222`
- Flame: `3996930be00b6cf17cd970fa32f6e97ba2216d6342a70827fb677adb06227c5f`

### Served lossless WebP SHA-256

- Telescope: `ca1f93afa46ccb0ffca6ae9c299434544663a750c17be735585220f14de3289f`
- Rocket: `53b40acf28cc36c3bb93dfe18b5eb1a611fd76a26647e6066949bc67a7560fd3`
- Flame: `89bcfd040e2d87ec573bb9d35e9ba0afe7496e0cb761af2882111c5c156cb39c`

## Generation direction (summary, not a verbatim prompt)

The coordinator requested authored transparent raster cartoons in the supplied reference's blue/steel/navy palette, with clear dark outlines, simple cel shading and readable silhouettes on black. The telescope was to read as a generic cartoon space telescope. The rocket points left; its body and matching flame were generated as separate transparent assets so exhaust can animate independently. Image-generation revisions cleaned the alpha edge and removed the generated white border, leaving border thickness to the display filter. No real photograph was cropped into the app as the new illustration.

---

# Superseded SPHEREx-inspired artwork

The following records the earlier asset for provenance. It is no longer referenced by the landing components.

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
