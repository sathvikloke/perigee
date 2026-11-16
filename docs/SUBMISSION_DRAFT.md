# Perigee submission draft

**Review status:** Prepared for owner review. Saving this draft does not submit it for judging.

## Project title

Perigee: Investigating the Infrared Sky

## Project summary

Perigee is a browser app where students investigate apparent changes in NASA SPHEREx images. A learner sees Barnard's Star shift against surrounding stars, then encounters a jumping dot in the WISE 0855 field. The second feature stays at one detector pixel as the telescope's pointing changes. Three guided investigations ask learners to check dates, wavelengths and pixel quality before recording their own explanation and comparing it with a reference. Each saved evidence card keeps that reasoning beside the selected observations and exact archive sources, so a teacher can examine how the conclusion was reached. Public object-name and coordinate search extend exploration beyond five prepared target fields. We checked the images and processing against the source FITS files and retained reproducible controls. Perigee's purpose is to make scientific reasoning something a learner can practice and someone else can inspect.

## Detailed project description

### A sky viewer for investigating apparent change

A learner can open Barnard's Star, press Play comparison and watch the bright glow shift against the surrounding stars. In the WISE 0855 field, another bright feature appears to jump. That feature stays at one detector pixel as the telescope's pointing changes. The two comparisons call for different explanations. Perigee puts dates, wavelengths and quality checks beside the images and asks the learner to record what they noticed, what supports their explanation and what remains uncertain. A teacher can inspect the saved reasoning with the observations that informed it.

Perigee answers the Planet X and SPHEREx challenge with a browser viewer for SPHEREx observations over time. Enter an object name or sky coordinates, retrieve the available observations from NASA/IPAC IRSA, and play or inspect the images on a common sky grid. Search accepts decimal and sexagesimal coordinates. Five prepared target fields provide an immediate starting point, and three guided investigations help a beginner decide what an apparent change means.

### Three investigations with useful decisions

Barnard's Star teaches a supported reading of apparent motion. Images from 25 August 2025 and 19 August 2026 show the glow shifting north at similar infrared wavelengths. Our visual controls reproduce the direction and approximate size of the catalog prediction while surrounding stars remain nearly fixed. The center is saturated, so the case supports a qualitative conclusion about the visible shift rather than a precise position or speed measurement.

Epsilon Indi B teaches how to choose a comparison that answers the question. One pair spans about five months at similar wavelengths. Another comes from the same exposure at 2.3232 and 4.9399 micrometers. The shared exposure time rules out change over time in that pair. Its wavelength, detector and display scale all differ, so the appearance does not isolate a wavelength effect. The learner records which comparison supports their explanation and which differences still need to be considered.

The WISE 0855 field teaches how to investigate a convincing apparent jump. The bright feature occupies detector pixel (1709, 1364) in both observations. Mapping that pixel through each exposure's sky-coordinate transform places it 5.36 arcseconds apart on the sky. The motion of three usable field stars across the detector predicts a 5.38-arcsecond sky shift for a detector-fixed feature, while their own sky positions agree within 0.76 arcseconds. The feature also carries adverse mission quality flags. Together, these checks support a detector-fixed explanation for the apparent jump. They do not establish the pixel's physical cause or identify the feature as WISE 0855. The learner can reject an unsupported moving-object claim with specific evidence.

### What Perigee contributes

Perigee connects image comparison to a learner-written explanation and preserves the context needed to check it. In Epsilon Indi B, a shared exposure time rules out a time-change explanation. In the WISE field, detector coordinates support an alternative to a moving celestial source. Those decisions depend on information the picture alone cannot supply. The learner records an explanation before opening the reference, then can compare the reasoning and revise the notes.

Notes save in the browser. The completed evidence record retains the learner's words, selected frame identifiers, observation dates, wavelengths, quality results and available display parameters. Archive links, file fingerprints and processing records connect the explanation to its inputs. JSON preserves the structured evidence, while print or Save as PDF creates a readable record. A teacher or classmate can check whether the conclusion follows from the observations without having to reconstruct which images the learner selected.

### NASA data and implementation

NASA/IPAC's Infrared Science Archive supplies SPHEREx Level 2 images from Data Release 1 and Quick Release 3. Our Python processor uses the FITS coordinate information to place observations on a fixed north-up sky grid, reads wavelength at the catalog-predicted detector position and preserves mission quality flags. Source URLs and raw-file SHA-256 fingerprints connect the displayed images to their archive inputs. SIMBAD supplies target information and astrometry. Gaia DR3 supplies field stars for an independent alignment check.

React, TypeScript and Vite provide the browser interface. Python, FastAPI, Astropy, NumPy and Pillow handle archive requests and image processing. Cloudflare serves the frontend and prepared cases, while Vercel hosts the Python service. Live search limits concurrent frame requests, retries transient failures and caches completed frames. The first ready image appears while the remaining observations load. Scientific processing is deterministic.

### Testing across the five challenge targets

We reviewed the identities, catalog positions, epochs, propagated markers and shipped frame records for Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis. The review gives each field a useful role. Barnard's Star supports apparent-motion comparison. Epsilon Indi B supports time-versus-wavelength comparisons. WISE 0855 provides the detector-fixed counterexample. RW Aurigae demonstrates why an unresolved binary needs system-level interpretation. R Draconis demonstrates the need to inspect saturation before a brightness comparison. Viewing the latter two fields does not by itself establish variability.

The historical source-file audit covered 189 processed records: 183 unique cutouts and six case re-renders. A separate code path re-derived timestamps, wavelengths, quality information, display mapping and provenance from the original FITS inputs. The independent field-star alignment screen returned 128 PASS, 55 UNKNOWN and zero FAIL verdicts across the 183 unique cutouts. PASS means the frame met this screen for substantial alignment errors. UNKNOWN means too few usable supporting stars. These results do not establish subpixel astrometric precision, source identity or a general error rate. Deliberate shifts of 1, 2 and 5 native pixels were rejected on all three tested real-frame fixtures, covering nine tested combinations.

### Who can use the result

A teacher can give a class the same pair of observations and ask students to explain what changed. Their saved records show which dates, wavelengths and quality evidence informed each answer. An astronomy club can debate the WISE feature, then use the retained control to test competing explanations. An independent learner can reopen notes, try a second case or search another object without installing software or creating an account.

The intended benefit is practice in turning an observation into a defensible explanation. The three cases exercise different decisions, while public name and coordinate search extends exploration beyond the prepared examples. Investigations use reusable case definitions. A repository admission tool checks frame references, provenance, metadata and quoted numerical values before a new case is added. Authors supply the scientific interpretation and its supporting evidence. These checks keep each reviewed activity tied to its source observations and supporting calculations.

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
