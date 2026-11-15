# Perigee submission draft

Status: first draft for team-owner review. Saving this page is separate from submitting for judging.

## Project name

Perigee: Investigating the Infrared Sky

## Summary

Perigee gives students, teachers and amateur astronomers a way to investigate NASA SPHEREx images and explain what they see. Start with Barnard's Star: play two observations and watch a bright source shift against the surrounding stars. Then check the dates, infrared wavelengths and pixel quality before writing a conclusion. Three guided cases explore apparent motion, differences between wavelengths and a misleading flagged feature. Each investigation ends with an evidence card that keeps the learner's explanation beside the observations, display settings and archive links. A teacher or classmate can follow the reasoning and inspect its sources. Built for the browser, Perigee connects the curiosity of noticing something in the sky with the care needed to interpret it.

## Project demonstration

https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf

## Project

https://perigee.lokesathvik.workers.dev/

## Project details

### From noticing a change to explaining it

Open the Barnard's Star investigation, press Play comparison, and watch the bright source change position relative to its neighbors. The next step is to work out what that change supports. Perigee keeps the dates, infrared wavelengths and pixel-quality checks beside the images, then asks the learner to record an explanation. For the Planet X and SPHEREx challenge, we built this experience for students, teachers and amateur astronomers: a short investigation that ends with reasoning another person can inspect.

A student opening public astronomy data has several choices to make before interpreting a difference. Images taken months apart and images taken at the same instant through different wavelength bands answer different questions. Display contrast can change apparent brightness, and a flagged pixel can resemble an interesting source. We put those distinctions into the task itself, so a beginner has a reason to check each piece of information before deciding what happened.

### Three investigations, three scientific judgments

Barnard's Star compares observations from August 2025 and August 2026 at similar infrared wavelengths. The bright glow shifts north relative to the surrounding stars, consistent with its catalog-predicted motion. Its saturated center limits the precision of that comparison. A supported explanation describes the visible shift and acknowledges that limit.

Epsilon Indi B asks the learner to distinguish a change in observation date from a change in wavelength. One pair spans about five months at similar wavelengths; another shares an exposure but uses different wavelengths and detectors. The same-time pair cannot establish change over time. Its display scales also differ, so the learner needs to account for contrast before interpreting brightness.

In the WISE 0855 field, a bright dot appears to jump between SPHEREx observations taken three days apart. The quality overlay marks the relevant pixel as unreliable, and our control check locates the feature at the same detector pixel in both exposures. These images do not establish a moving celestial object. The case gives a student a concrete reason to examine quality information even when an image looks convincing.

### An explanation someone else can inspect

The notebook begins with what the learner noticed. They record an observation, an explanation and remaining uncertainty, then compare their response with the case reference. Notes save in the browser. An exported evidence card keeps those words with the selected frame identifiers, dates, wavelengths, quality results and display settings, plus archive links and processing records. A teacher can inspect which observations a student used and how they reached the conclusion. A classmate can revisit the source images and question the interpretation.

The app opens without an account or installation. A teacher or astronomy club can use one case for a short activity, while an interested learner can return to the other cases, explore five named target fields, or search by object name or coordinates. Curated investigations contain processed archive observations. Live searches load frames as they become available, with limited concurrency, retries for transient failures and caching of completed frames.

### NASA data and implementation

NASA/IPAC's Infrared Science Archive supplies SPHEREx Level 2 images from DR1 and QR3. Our Python processor places observations on a fixed sky grid, reads wavelength at the catalog-predicted native target position and preserves mission quality flags. It retains source URLs and file hashes so a reviewer can trace a displayed comparison back to its archive inputs. SIMBAD supplies catalog information and target astrometry; Gaia DR3 provides field stars for an independent alignment check.

We built the browser interface with React, TypeScript and Vite, and the archive service with Python and FastAPI. Astropy, NumPy and Pillow support FITS processing and image generation. Cloudflare hosts the frontend, and Vercel hosts the Python service. The running application uses deterministic processing rather than an AI model to interpret observations.

### Checks behind the comparisons

We checked processing consistency against the original FITS files and tested image alignment against Gaia field stars. Across 183 unique cutouts, the independent registration check returned 128 PASS, 55 UNKNOWN and no FAIL verdicts. UNKNOWN means too few supporting stars for a verdict. Tests with deliberate displacements caught all nine tested combinations of three frames and shifts of 1, 2 and 5 native pixels. The technical report contains the methods, figures and conditions under which those checks apply.

### Intended impact

Our contribution is the connection between a learner's explanation and the observations used to support it. A completed investigation gives a student something they can explain and a teacher something they can question: a conclusion with its evidence attached. The same workflow can support classroom discussion, astronomy-club activities and independent exploration of public NASA data.

### Development and image credits

Claude Code and OpenAI Codex assisted implementation, testing, scientific review scripts and writing. OpenAI image generation produced the labelled decorative telescope and rocket artwork. Investigation images come from the SPHEREx archive. The repository documents the tools and assistance used. We acknowledge NASA/JPL/Caltech and NASA/IPAC IRSA for SPHEREx data, CDS for SIMBAD, and ESA and the Gaia collaboration for Gaia DR3.

### Supporting materials

- [Seven-slide demonstration](https://perigee.lokesathvik.workers.dev/demo/perigee-demo.pdf)
- [Technical report: methods, figures and validation](https://perigee.lokesathvik.workers.dev/demo/perigee-technical-report.pdf)
- [Source code and scientific checks](https://github.com/sathvikloke/perigee)
- [AI-use notes](https://github.com/sathvikloke/perigee/blob/main/docs/AI_USE.md)

## NASA data

- [SPHEREx DR1 Spectral Images - dataset DOI](https://www.ipac.caltech.edu/doi/10.26131/IRSA678)
- [SPHEREx QR3 Spectral Images - dataset DOI](https://www.ipac.caltech.edu/doi/10.26131/IRSA662)
- [NASA/IPAC IRSA SPHEREx Archive](https://irsa.ipac.caltech.edu/Missions/spherex.html)
- [SPHEREx Archive Data Access Documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)
- [IRSA SPHEREx Image Tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro)
- [JPL SPHEREx Spacecraft Reference](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/)

## Space agency partner and other resources

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
- [Complete software, design, document and tool credits](https://github.com/sathvikloke/perigee/blob/main/docs/SUBMISSION_RESOURCES.md)

The form permits 25 partner/other-resource rows. The final link includes ReportLab, pypdf and Sharp, along with the full dependency and tool list.

## Existing SI-use selections

Coding, Debugging, or Troubleshooting; Visual Design or Image Creation; Presentation, Video, or Audio; Other Project-Related SI Use. These describe the existing selections in the form. They do not assert that a video has been recorded.

## Review and submission

The team owner must review the saved draft before submitting. The current form lists the deadline as 15 November 2026 at 11:59 PM in the Chicago local-event time zone. No Submit for Judging action is authorized in this draft task.
