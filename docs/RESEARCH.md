# Research and feasibility

This document records research findings. It does not certify scientific measurements or establish demand for the product.

# What is distinct, and what already exists

| Closest existing work | What it already covers | Perigee’s contribution to demonstrate |
|---|---|---|
| IRSA’s SPHEREx interface and documentation | Archive access, images, flags, provenance, and spectrophotometry | A short, coherent investigation for a learner, ending in their own supported conclusion |
| SPXQuery and SPHEREx analysis packages | Programmatic retrieval and analysis workflows | A browser experience without requiring Python or archive expertise |
| SPHEREx timelapse and blink projects | Time browsing, image comparison; some also include masks, differences, curves, or exports | Put observation date, wavelength, quality, and the learner’s reasoning into the same guided flow |
| Driftnet and similar Planet X projects | Overlapping motion-review and evidence-report concepts | Do not claim evidence cards alone are new; demonstrate the complete educational interaction |
| Rubin and Zooniverse | Guided authentic-data education and public participation | Apply that approach carefully to SPHEREx’s particular time/wavelength/quality constraints |

References reviewed include [IRSA spectrophotometry](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html), [SPXQuery](https://spxquery.readthedocs.io/en/latest/), [SPHEREx timelapse](https://github.com/ShivenKhurana1/spherex-timelapse), [SPHEREx Blink](https://andrei25ciuta.github.io/SPHEREx/results.html), and [Driftnet](https://spherex-planet-x.vercel.app/about/). These comparisons are based on published interfaces, documentation, and selected code inspection, not a full performance benchmark of every project.

**Defensible contribution:** a focused educational workflow that helps a newcomer make and document a scientifically cautious comparison using real SPHEREx data. This is a proposed improvement in usability and learning, not an exclusive technical invention. The weekend must demonstrate that improvement. Do not claim “first SPHEREx citizen-science platform,” “first time viewer,” or “first evidence report.” NASA has also selected a SPHEREx-related citizen-science effort, Rogue Worlds. [NASA’s 2026 citizen-science selections](https://science.nasa.gov/get-involved/citizen-science/nasa-selects-19-new-citizen-science-proposals-in-2026/).

# What the research and downloads actually establish

The decision pass reviewed the challenge and current judging/submission rules, the official descriptions of 30 global winners from 2023–2025, relevant competing viewers and educational workflows, SPHEREx archive/access/quality documentation, and the feasibility of the earlier outburst proposal. Winner descriptions show recurring combinations of a clear purpose, tangible experience, relevant science/data, and understandable presentation; they do not establish a causal winning formula. Losing entries and private judge scores were not available for a controlled comparison. [2023 winners](https://science.nasa.gov/directorates/smd/2023-nasa-international-space-apps-challenge-announces-10-global-winners/), [2024 winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-international-space-apps-challenge-announces-2024-global-winners/), [2025 winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).

**Downloaded source data:** 1,986 returned archive metadata records across five target positions, querying DR1 and QR3 wide-survey collections. From 188 selected cutout requests, 183 FITS files downloaded successfully; five requests returned HTTP 503 after retries. The original FITS files, archive metadata, source URLs/hashes, and official explanatory-supplement PDF remain local. Generated previews, frontend manifests, case files, preparation scripts, and the old starter ZIP have been removed. Build the application and processing pipeline from scratch during the event.

| Target | Saved FITS cutouts | Adequate central coverage | Central apertures passing the conservative screen |
|---|---:|---:|---:|
| Barnard’s Star | 34 | 34 | 0 |
| Epsilon Indi B | 44 | 43 | 29 |
| WISE 0855 | 34 | 34 | 21 |
| RW Aurigae | 35 | 33 | 1 |
| R Draconis | 36 | 35 | 0 |

The screen counts finite, sufficiently covered pixels without selected adverse flags near a catalog-predicted position. It is not a source-detection test or certified photometry. The bright-star flags and the earlier outburst data’s quality problems are reasons to keep quantitative scientific inference out of the critical path.

All 183 downloaded FITS files were structurally read and their SHA-256 hashes verified during the data audit. The audit also checked coordinate consistency and inspected candidate images. Those observations inform the research findings below, but the display pipeline and generated assets have been removed. A new implementation still needs its own validation; the audit does not establish calibrated fluxes or discovery performance.

Earlier work separately inspected 1,406 archive records, 1,544 NEOWISE rows, and 25 successful FITS downloads for three outburst-oriented targets. Published work already combines NEOWISE and SPHEREx in this area, while good photometry can require coadds, deblending, additional spectra, and stronger validation. The earlier files remain available, but they are not the weekend dependency. [Relevant outburst study](https://arxiv.org/abs/2602.07129), [NEOWISE quality documentation](https://irsa.ipac.caltech.edu/data/WISE/docs/release/NEOWISE/expsup/sec2_3.html).

This was a targeted feasibility audit, not a scan of all NASA data. It did not exhaust SPHEREx’s deep fields, all-sky positions, every wavelength/epoch pairing, or every competitor’s code. No PSF-matched photometry, measured proper motion, sensitivity-calibrated nondetection, prospective user study, or live application test has been completed. Further exhaustive archive exploration would not remove the immediate need to build and test the chosen interaction.
