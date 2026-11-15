# Perigee submission draft

**Review status:** Prepared for owner review. Saving this draft does not submit it for judging.

## Project title

Perigee: Investigating the Infrared Sky

## Project summary

Perigee turns an object name or sky position into a sequence of NASA SPHEREx images that anyone can explore in a browser. A student watches Barnard's Star shift between observations, then asks whether the images support that conclusion. Perigee puts the dates, infrared wavelengths and pixel-quality checks beside the comparison. Three guided investigations help learners recognize apparent motion, choose a fair comparison and investigate a misleading dot. The learner finishes with an explanation linked to the exact observations, display settings and archive sources. A teacher or astronomy-club leader can inspect both the conclusion and its evidence. We tested the viewer across all five challenge target fields and retained reproducible processing checks. Our contribution connects public data access with a short investigation whose reasoning can be saved, shared and questioned.

## Detailed project description

### A public sky viewer with a question to investigate

Perigee answers the Planet X and SPHEREx challenge with a browser viewer for SPHEREx observations over time. Enter an object name or sky coordinates, retrieve the available observations from NASA/IPAC IRSA, and play or inspect the images on a common sky grid. Search accepts decimal and sexagesimal coordinates. Five prepared target fields provide an immediate starting point, and three guided investigations help a beginner decide what an apparent change means.

Imagine a student opening Barnard's Star. They press Play comparison and see the bright glow shift against the surrounding stars. Before calling it motion, they need to know when the images were taken, which infrared wavelengths they show and whether the relevant pixels are reliable. Perigee puts those checks beside the image and follows them with a notebook. The student leaves with an explanation and the observations behind it. A teacher can ask why the student reached that conclusion and inspect the same evidence.

### Three investigations with useful decisions

Barnard's Star teaches a supported reading of apparent motion. Images from 25 August 2025 and 19 August 2026 show the glow shifting north at similar infrared wavelengths. Our visual controls reproduce the direction and approximate size of the catalog prediction while surrounding stars remain nearly fixed. The center is saturated, so the case supports a qualitative conclusion about the visible shift rather than a precise position or speed measurement.

Epsilon Indi B teaches how to choose a comparison that answers the question. One pair spans about five months at similar wavelengths. Another comes from the same exposure at 2.3232 and 4.9399 micrometers. The same-time pair explores wavelength differences. It cannot establish change over time, and its display scales must be considered before comparing gray levels. The learner records which comparison supports their explanation.

The WISE 0855 field teaches how to investigate a convincing apparent jump. A bright feature changes its sky position by 5.36 arcseconds between two observations, but occupies the same detector pixel in both. Three usable field stars imply a 5.38-arcsecond apparent shift for a detector-fixed feature as the pointing changes, while their own sky positions agree within 0.76 arcseconds. The feature also carries adverse mission quality flags. Together, these checks support a detector-fixed explanation for the apparent jump. They do not establish the pixel's physical cause or identify the feature as WISE 0855. The learner can reject an unsupported moving-object claim with specific evidence.

### What Perigee contributes

Archive viewers and astronomy education projects already provide image comparison, quality information and guided activities. Perigee's contribution is the continuous path from a SPHEREx comparison to a learner-written explanation with its exact sources attached. The notebook begins with what the learner noticed, then asks what it supports and what remains uncertain. A reference explanation appears after the learner records their own reasoning.

Notes save in the browser. The completed evidence record retains the learner's words, selected frame identifiers, observation dates, wavelengths, quality results and display settings. Archive links, file fingerprints and processing records allow someone else to revisit the inputs. JSON preserves the structured evidence, while print or Save as PDF creates a readable record. This makes a conclusion inspectable outside the app, with enough context for a teacher or classmate to challenge it.

### NASA data and implementation

NASA/IPAC's Infrared Science Archive supplies SPHEREx Level 2 images from Data Release 1 and Quick Release 3. Our Python processor uses the FITS coordinate information to place observations on a fixed north-up sky grid, reads wavelength at the catalog-predicted detector position and preserves mission quality flags. Source URLs and raw-file SHA-256 fingerprints connect the displayed images to their archive inputs. SIMBAD supplies target information and astrometry. Gaia DR3 supplies field stars for an independent alignment check.

React, TypeScript and Vite provide the browser interface. Python, FastAPI, Astropy, NumPy and Pillow handle archive requests and image processing. Cloudflare serves the frontend and prepared cases, while Vercel hosts the Python service. Live search limits concurrent frame requests, retries transient failures and caches completed frames. The first ready image appears while the remaining observations load. Scientific processing is deterministic.

### Testing across the five challenge targets

We reviewed the identities, catalog positions, epochs, propagated markers and shipped frame records for Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis. The review gives each field a useful role. Barnard's Star supports apparent-motion comparison. Epsilon Indi B supports time-versus-wavelength comparisons. WISE 0855 provides the detector-fixed counterexample. RW Aurigae demonstrates why an unresolved binary needs system-level interpretation. R Draconis demonstrates the need to inspect saturation before a brightness comparison. Viewing the latter two fields does not by itself establish variability.

The historical source-file audit covered 189 processed records: 183 unique cutouts and six case re-renders. A separate code path re-derived timestamps, wavelengths, quality information, display mapping and provenance from the original FITS inputs. The independent field-star alignment audit of the 183 unique cutouts returned 128 PASS, 55 UNKNOWN and zero FAIL verdicts. UNKNOWN means too few usable supporting stars. These verdicts assess alignment, not source identity or the scientific validity of every comparison. Deliberate shifts of 1, 2 and 5 native pixels were rejected on all three tested real-frame fixtures, covering nine tested combinations.

### Who can use the result

A teacher can give a class the same pair of observations and ask students to explain what changed. Their saved records show which dates, wavelengths and quality evidence informed each answer. An astronomy club can debate the WISE feature, then use the retained control to test competing explanations. An independent learner can reopen notes, try a second case or search another object without installing software or creating an account.

The intended benefit is practice in turning an observation into a defensible explanation. The three cases exercise different decisions, so returning means investigating another question. Public name and coordinate search extends exploration beyond the prepared examples. The portable evidence record gives the activity a concrete result that can be discussed or reused.

### Development and image credits

Sathvik Loke, Sagar Raut, Akshobya Rao, Aditya Raut, Suhrit Bestavemula and Neeraj Movva built Perigee. Our team developed the idea through its research. Claude Code and OpenAI Codex assisted implementation, tests, scientific review scripts and writing. We monitored the work AI completed and kept revising. OpenAI image generation produced the labeled decorative telescope and rocket artwork. The investigation images come from the SPHEREx archive. We acknowledge NASA/JPL/Caltech and NASA/IPAC IRSA for SPHEREx data, CDS for SIMBAD and Sesame, and ESA and the Gaia collaboration for Gaia DR3. The linked resource list and AI-use notes record the tools and assistance used.

### Supporting materials

- [Seven-slide demonstration](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf)
- [Technical report (10 pages): methods, figures and validation](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf)
- [Source code and reproducible scientific checks](https://github.com/sathvikloke/perigee)
- [AI-use notes](https://github.com/sathvikloke/perigee/blob/main/docs/AI_USE.md)

## Submission links

- **Link to Final Project:** https://perigee.lokesathvik.workers.dev/
- **Link to Project Demo:** https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf
- The seven-slide deck is the current demo link. Add a recorded video only after its public URL and duration are verified.

## NASA resources

- [SPHEREx DR1 Spectral Images - dataset DOI](https://www.ipac.caltech.edu/doi/10.26131/IRSA678)
- [SPHEREx QR3 Spectral Images - dataset DOI](https://www.ipac.caltech.edu/doi/10.26131/IRSA662)
- [NASA/IPAC IRSA SPHEREx Archive](https://irsa.ipac.caltech.edu/Missions/spherex.html)
- [SPHEREx Archive Data Access Documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)
- [IRSA SPHEREx Image Tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro)
- [JPL SPHEREx Spacecraft Reference](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/)

## Other resources

- [ESA Gaia DR3 - field-star reference catalog](https://www.cosmos.esa.int/web/gaia/dr3)
- [CDS SIMBAD - target catalog (Harvard mirror)](https://simbad.cfa.harvard.edu/simbad/)
- [CDS Sesame - object-name resolution](https://cds.unistra.fr/cgi-bin/Sesame)
- [React](https://react.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/)
- [Python](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Astropy](https://www.astropy.org/)
- [NumPy](https://numpy.org/)
- [Pillow](https://python-pillow.org/)
- [HTTPX](https://www.python-httpx.org/)
- [Pydantic](https://docs.pydantic.dev/latest/)
- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [Vercel](https://vercel.com/docs)
- [Vitest](https://vitest.dev/)
- [pytest](https://docs.pytest.org/en/stable/)
- [Claude Code](https://code.claude.com/docs/en/overview)
- [OpenAI Codex](https://openai.com/codex/)
- [OpenAI image generation](https://openai.com/index/introducing-4o-image-generation/)
- [Impeccable design instructions](https://github.com/pbakaus/impeccable)
- [Avoid AI Writing - editorial instructions](https://github.com/conorbronsdon/avoid-ai-writing)
- [Stop Slop - editorial instructions](https://github.com/hardikpandya/stop-slop)
- [Tectonic - LaTeX compiler](https://tectonic-typesetting.github.io/)
- [Project dependency manifests and complete tool credits](https://github.com/sathvikloke/perigee/blob/main/docs/SUBMISSION_RESOURCES.md)

## Scientific and editorial source record

- [Five-target review](../science/reviews/targets/README.md).
- [Source-file acceptance](../science/reviews/acceptance/README.md).
- [Independent alignment audit](../science/reviews/registration-audit/README.md).
- [Retained controls and numerical results](../science/reviews/overnight-controls/README.md).
- [Comparison with existing work](../science/reviews/contribution/README.md).
- [Demo content requirements](presentation/SUBMISSION_CONTENT_RULES.md).

## Form handoff

Retain the six NASA rows and 25 other-resource rows above. The final other-resource link preserves the complete credits, including ReportLab, pypdf and Sharp. Keep the existing SI selections for coding/debugging, visual design, presentation/video/audio and other assistance. The owner must review the responses and required attestations before any Submit for Judging action.
