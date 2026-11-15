# Perigee
## Guided investigation of SPHEREx images

Technical report | NASA Space Apps 2026 | 15 November 2026

Sathvik Loke, Sagar Raut, Akshobya Rao, Aditya Raut, Suhrit Bestavemula and Neeraj Movva

## Purpose

A student sees a bright feature shift between two astronomical images. The next task is to decide what that difference supports. Observation time, wavelength, display contrast and unreliable pixels can change the appearance of a source. Perigee places those checks beside the comparison and gives the learner a place to write an explanation that retains its source observations.

The intended audience is students, teachers and astronomy clubs. A learner can compare NASA SPHEREx images, record an observation and uncertainty, and export an evidence card. A teacher can inspect the reasoning and the data behind it. This is a proposed educational benefit. The project has not measured learning gains, classroom use or retention.

## Contribution and scope

Perigee combines a coordinate-based archive viewer, three guided investigations and a learner-authored evidence record. The distinctive contribution proposed here is the saved explanation connected to exact frame provenance. Archive search, image blinking, quality masks and astronomical education already exist in other tools. The repository's comparison with SPHEREx Explorer found extensive overlap and a narrower difference in editable, exportable learner reasoning; that review was partly limited to static code and API inspection. [1, 8]

The scientific result is a reproducible set of teaching comparisons and checks on their processing. Perigee does not claim a new astronomical discovery or a new method for measuring proper motion. Its visual previews support qualitative investigation; they are not calibrated photometry.

| Evidence in this report | Scope |
| --- | --- |
| 183 retained unique cutouts | Five target fields; selected examples, not an all-sky survey |
| 128 PASS / 55 UNKNOWN / 0 FAIL | Independent field-star registration verdicts on those cutouts |
| Three guided investigations | Apparent motion, wavelength comparison and a flagged feature |
| Deterministic controls | Display mapping, source quality and comparison context; no learner trial |

This report documents a hackathon prototype and its retained experiments. It is supporting technical documentation, not a peer-reviewed paper. The public app and source are linked on page 8. Deployment status can change after this document is built.

---PAGE---
# Data and processing

## Inputs and provenance

The image source is SPHEREx Level 2 data from NASA/IPAC IRSA, using Data Release 1 and Quick Release 3. Archive search uses IRSA's Simple Image Access service; individual frame requests obtain small FITS cutouts. The retained set covers Epsilon Indi B, Barnard's Star, WISE 0855, RW Aurigae and R Draconis. Each record retains its observation ID, detector, collection, original URL, cutout URL, retrieval time and SHA-256 hash. Raw FITS files remain outside Git. [2, 3, 9]

SIMBAD supplies target positions and proper motions. The marker is a catalog prediction propagated to the observation epoch, not a detection fitted to the image. Gaia DR3 supplies a separate set of field stars for registration checks. Annual parallax is not included in the target propagation. [4, 5, 10]

<!-- figure: pipeline -->

## FITS to browser frame

The pure processor accepts original FITS bytes and metadata, then returns PNG bytes and a JSON frame record. It performs no network requests. It reads IMAGE, VARIANCE and FLAGS extensions and mid-exposure DATE-AVG / MJD-AVG timestamps. It checks file identity and detects truncated data units before processing. A spectral lookup index must be finite and strictly monotonic before WCSLIB evaluates it. [9]

Images are sampled onto a fixed tangent-plane sky grid, north up and east left, centered on the query. The default field is 6 arcminutes across 256 pixels, or 1.40625 arcseconds per display pixel. Nearest-neighbor sampling preserves the discrete native pixel structure; a larger display does not add angular resolution. The grid stays fixed as the target moves.

Wavelength and bandwidth are evaluated at the predicted native position using the alternate spectral WCS and WCS-WAVE table, with celestial SIP distortion removed for this lookup. Off-image positions return no wavelength. These table values are appropriate for visualization and do not establish a calibrated spectrum. [3, 9]

The display applies a normalized asinh stretch with softening 10, using the 1st and 99.5th percentiles unless shared limits are supplied. Shared case limits allow the same physical input value to receive the same grey level. A per-frame stretch is labeled because greys cannot then be compared directly. The processor makes no background subtraction and no photometric measurement.

---PAGE---
# Two comparisons with different questions

## Barnard's Star: apparent motion

The moving_neighbor case compares three D3 observations: 25 August 2025, 19 March 2026 and 19 August 2026, at approximately 2.0062, 2.0123 and 2.0284 micrometers. The dates and nearly matched wavelengths make the pair useful for a visual time comparison. A and C span about one year and share the case's display scale. They also span DR1 and QR3, so processing differences remain part of the context. [6, 11]

<!-- figure: barnard -->

The catalog prediction shifts A to C by 7.29 display pixels, about 10.25 arcseconds. Across 11 deliberately varied glow proxies, the shift is 6.87 to 8.87 display pixels toward north; the selected field stars move at most 0.83 display pixels. This supports a visible relative shift consistent with the predicted direction. The full set of proxy results is reported, including method-dependent disagreement. [11, 12]

Barnard's core is saturated and flagged. A center computed from its glow depends on the window and treatment of non-finite pixels. It is a visual consistency check, not a centroid measurement, a proper-motion estimate or a speed. All 34 retained Barnard cutouts pass the independent field-star registration check; this is separate evidence from the moving glow itself. [10]

## Epsilon Indi B: time versus wavelength

The fair_comparison case uses A and B from 29 April and 27 September 2026 at 2.3232 and 2.3220 micrometers. A and C instead share the same April exposure, while C is on D6 at 4.9399 micrometers. A visual difference between A and C therefore cannot be described as a change over time. The pair also has different detector response and display scaling. [6, 12]

Frame C remains UNKNOWN for independent field-star registration because too few stars meet the signal-to-noise threshold. A same-exposure, different-detector control places the target within 0.15 arcseconds between C and Gaia-checked A, but this tests one location and assumes A is correct. It does not validate rotation or scale across C's field. [10]

The learner's task is to name the comparison being made and its limits. Neither a changing grey value nor a lack of visible change establishes quantitative variability.

---PAGE---
# A flagged feature and controlled checks

## WISE 0855 field: a dot that jumps

The third investigation uses SPHEREx observations of the WISE 0855 field. It does not use WISE-mission images. The first pair is from 7 and 10 November 2025 at nearly the same target wavelength, about 1.2572 micrometers; the third observation is from 11 May 2026 at about 1.4443 micrometers. The near-marker dot is not identified as WISE 0855. [6]

In the first pair, one flagged feature occupies the same detector pixel, (1709, 1364), but lands 5.36 arcseconds apart on the common sky grid. Three usable field stars agree within 0.76 arcseconds. Their detector displacement predicts a 5.38-arcsecond shift for a detector-fixed pixel. This comparison supports treating the apparent jump as unreliable evidence for a moving celestial source. It does not determine the physical cause of the flag. [12]

The feature carries TRANSIENT, SUR_ERROR and NONFUNC flags in both observations; an additional SOURCE bit in the first is informational. A source-mask label is not a new detection. The small target quality screen and this off-target feature are separate locations, so a target status alone cannot certify every pixel in the image.

## Deterministic counterexamples

| Check | Retained result | Interpretation |
| --- | --- | --- |
| Display stretch | 1.0 MJy/sr maps to grey 156 versus 174 with two per-frame stretches; 159 in both with shared limits | Equal values can look different when each image chooses its own contrast |
| Time and wavelength | First WISE-field pair differs by 2.655 days and 0.0018 bandwidths | Wavelength is closely matched; time, pointing, quality, processing build and stretch still differ |
| Same exposure | Epsilon A/C are 69.6 bandwidths apart on different detectors | A wavelength comparison cannot be narrated as temporal change |
| Positive motion control | Every Barnard proxy points north; field-star displacement is much smaller | The workflow can support a qualitative movement conclusion while retaining saturation limits |

The original control run found that the physical background in the second WISE-field image was about 0.971 times the first. Its cause is not established. Shared stretching fixes a display inconsistency; it does not make the observations physically identical. [12]

An authored information-removal matrix compares 16 questions across 11 representations. Time, wavelength, scale, quality and provenance each supply information needed by specific questions. Cause, identity, proper motion and photometry remain unsupported by every representation. This is an audit of available information, not a measurement of how learners use it. The selected controls are teaching counterexamples, not a representative survey or accuracy benchmark.

---PAGE---
# Independent registration and consistency

## Counts and denominators

<!-- figure: validation -->

The historical acceptance sweep contains 189 records: 183 unique retained cutouts and six repeated case copies. Its original seven columns check agreement with the FITS bytes, metadata and stated rendering method. All 189 passed those internal consistency checks. Reconstructing an image from its own WCS header can reproduce a shared error, so that result must not be presented as 189 independent astrometric passes. [7, 10]

The separate registration audit uses detections whose eligibility does not depend on the WCS or catalog. It votes on their common offset from Gaia DR3 positions and checks for rotation. The unique-cutout result is 128 PASS, 55 UNKNOWN and 0 FAIL. With case copies included, the corresponding record counts are 133, 56 and 0. UNKNOWN is retained as uncertainty, never counted as a pass.

## Controls and sensitivity

| Test | Result and boundary |
| --- | --- |
| Deliberately shifted real pixels | Every tested 1, 2 and 5 native-pixel shift failed on three selected frames |
| Legacy blind spot | Some 2- and 5-pixel shifts passed the old header-based check after the Gaia associations disappeared |
| Sparse support | Fewer than three detections or supporting matches produces UNKNOWN |
| Small offsets | Shifts of 0.5 native pixels or less are not reliably rejected |
| Rotation | About 1 degree is detected only in sufficiently rich fields; sparse fields can fail or remain unknown at 3 degrees |

Thresholds were chosen after examining the retained real frames and before testing the perturbation fixtures. They are not a held-out estimate of generalization. The check flags an offset above 0.6 native pixels at more than four standard errors; rotation criteria use support and significance thresholds. Exact rules and the full perturbation table are in the registration audit. [10]

The earlier selected-match analysis retained 958 stars in 156 unique frames and found a median PNG residual of 0.45 display pixels. Selection used signal-to-noise and association cuts; this statistic does not characterize the 27 frames with no retained matches, and is not the denominator for the stricter 128-pass verdict.

The acceptance sweep also reproduced timestamps, wavelength lookup, mask overlays, geometric coverage, display mapping and file hashes. Four records were geometrically not covered. Saturation at a covered target remains a quality issue, rather than being relabeled as missing coverage. These results concern the retained products, not the live API or every future archive frame.

---PAGE---
# Interface, reliability and scientific limits

## A learner-authored result

The interface brings the next instruction close to the images, then asks the learner what changed, what the observations support and what remains uncertain. Date comparisons, playback, wavelength labels and optional flagged-pixel overlays support those checks. The reference explanation appears after the learner records an answer; it is not an automatic scientific verdict.

The evidence card preserves the latest notes, selected frames, observation time, target wavelength, quality summary, display settings and provenance. It can be saved locally, exported as JSON and printed to PDF. The local record is not a shared classroom service, and it does not retain a full revision history. A teacher would need the exported card or access to the same device to read it. [8, 13]

## Two delivery paths

Curated investigations use bundled processed archive observations and can demonstrate the complete workflow without fetching each FITS file during the session. General exploration resolves object names or accepts sky coordinates, searches the archive and processes returned frames. Those live requests add external service and network dependencies. The existence of bundled cases does not remove the live-search requirement of the challenge. [1, 9]

During the coordinator's 15 November release review, the nonpreset Orion search returned 502 in three smoke runs. The API's read timeout is 20 seconds within a 25-second overall budget; a matching direct IRSA request returned after 21.1 seconds. These probes indicate slow or intermittent archive responses, not that every request fails. The curated investigation data remained available. This report does not claim that the timeout has been fixed. [14]

## Limits that affect interpretation

| Boundary | Consequence |
| --- | --- |
| Display previews | No flux, magnitude, variability amplitude, detection significance or proper-motion measurement |
| Quality screen | Tests a 2.5-native-pixel circle at one position; a clear status does not establish a source detection or certify the whole frame |
| Catalog marker | Depends on supplied astrometry and propagation; annual parallax is omitted |
| Registration UNKNOWN | Insufficient independent evidence must remain visible, including the Epsilon D6 case |
| Selection | Five chosen fields and selected comparisons cannot support all-sky reliability claims |
| Educational outcome | No classroom trial, adoption measurement or task-time comparison has been run |

The next research step is a small, consented learning study using an unfamiliar comparison and a predefined reasoning rubric. The question would be whether learners can identify relevant checks and state a bounded conclusion. This is a proposed evaluation, not a completed experiment. Live archive reliability also needs a measured timeout and recovery study before a stronger availability claim is made.

---PAGE---
# Reproduction and inspection

## Source layout

| Repository path | What a reviewer can inspect |
| --- | --- |
| backend/data/process.py | FITS parser, fixed-grid sampling, spectral lookup, flags, stretch and frame provenance |
| backend/data/archive.py | IRSA search and cutout access |
| backend/content/cases/ | Three case definitions, selected observations, sources and limits |
| science/reviews/acceptance/ | Historical consistency sweep and corrected independent astrometry column |
| science/reviews/registration-audit/ | Blind field-star check, negative controls, residuals and verdicts |
| science/reviews/overnight-controls/ | Five deterministic counterexamples and input/output manifests |
| science/reviews/contribution/ | Bounded comparison with existing tools |
| frontend/src/components/Notebook.tsx | Learner notes and evidence workflow |

## Re-run the scientific checks

Install the repository's Python requirements and Pillow in a virtual environment. The retained raw FITS directory must contain the manifest and cutouts named by the review scripts; it is not included in Git. Cached Gaia controls and published results are in the repository. Set DATA to that local data directory and choose fresh output directories, because the audit scripts refuse non-empty destinations.

```sh
python science/reviews/acceptance/check_acceptance.py \
  --data-root "$DATA" --all --out /tmp/acceptance-review.json

python science/reviews/registration-audit/audit_registration.py \
  --data-root "$DATA" --out-dir /tmp/registration-review

python science/reviews/overnight-controls/run_controls.py \
  --data-root "$DATA" --out /tmp/controls-review

PERIGEE_BUILD_DATA="$DATA" python -m pytest \
  science/reviews/registration-audit/tests -q -p no:cacheprovider
```

These commands reproduce existing experiments; this report does not claim a new run. The committed overnight-control environment records Python 3.12.16, NumPy 2.5.4, Astropy 8.0.2 and Pillow 13.0.0. A pair of fresh control runs matched numerically, with manifest differences for timestamps, runtime and output path; OS fonts can alter figure pixels. [12]

To inspect provenance without the raw dataset, open a case JSON and its frame records, follow the archive links and compare observation IDs, release, detector and hash fields. Re-downloading the exact retained bytes is required for a matching cutout hash. A different archive build or cutout request can yield different bytes.

This report is built from TECHNICAL_REPORT.md with build_report.py. The build uses ReportLab for layout, the repository's original processed PNGs for the Barnard figure and native vector drawings for the pipeline and validation count chart. It writes eight pages and checks that count. No generated astronomical image is used.

---PAGE---
# References and artifact links

## Mission data and catalogs

[1] NASA Space Apps. Planet X and SPHEREx challenge, 2026. https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/

[2] NASA/IPAC IRSA. SPHEREx archive and DR1 overview. https://irsa.ipac.caltech.edu/Missions/spherex.html ; https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html

[3] Caltech/IPAC. SPHEREx data access and tutorial. https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/ ; https://caltech-ipac.github.io/irsa-tutorials/spherex-intro

[4] CDS. SIMBAD astronomical database; target identities and catalog astrometry. https://simbad.cds.unistra.fr/ ; https://simbad.cfa.harvard.edu/simbad/

[5] ESA. Gaia Data Release 3. https://www.cosmos.esa.int/web/gaia/dr3 ; https://gea.esac.esa.int/archive/

## Perigee methods and retained evidence

All paths below are relative to https://github.com/sathvikloke/perigee . Each source is available through the repository. The report describes the retained 14-15 November 2026 reviews and the release observations stated on page 6.

[6] Case definitions: backend/content/cases/moving_neighbor.json ; fair_comparison.json ; wise_0855_quality_trap.json . Each contains frame URLs, timestamps and SHA-256 identifiers.

[7] Historical acceptance and corrected scope: science/reviews/acceptance/README.md ; check_acceptance.py . The original 189-record consistency count includes six case copies.

[8] Closest-work comparison: science/reviews/contribution/README.md . Includes access limits for the SPHEREx Explorer review and the untested educational contribution.

[9] Processing and archive access: backend/data/process.py ; backend/data/archive.py ; backend/routes/ . Processor version perigee-processor-a/0.1.2.

[10] Independent registration: science/reviews/registration-audit/README.md ; audit_registration.py ; regcheck.py ; results/ ; tests/test_negative_control.py . Documents PASS, UNKNOWN, FAIL and injected-error sensitivity.

[11] Barnard review: science/reviews/barnard/README.md . Read alongside the later proxy and registration audits rather than as a precision astrometric result.

[12] Deterministic controls: science/reviews/overnight-controls/README.md ; run_controls.py ; results/results.json ; results/manifest.json . Full tables and derived figures retain the stated limitations.

[13] Evidence-card implementation and checks: frontend/src/components/Notebook.tsx ; qa/production-journey/ ; qa/cloudflare-release/ ; docs/presentation/rehearsal/evidence-card-fair_comparison.json . Historical QA does not certify a later deployment.

[14] Release observations: qa/landing-motion/RELEASE.md . Records the 15 November public smoke checks and direct-IRSA timing; these are bounded probes, not a service benchmark.

## Project and acknowledgment

Public app: https://perigee.lokesathvik.workers.dev/

Source and AI-use notes: https://github.com/sathvikloke/perigee ; https://github.com/sathvikloke/perigee/blob/main/AI_USE.md

This product uses SPHEREx data, a NASA mission managed by JPL/Caltech, obtained from NASA/IPAC IRSA, operated by Caltech under contract with NASA. SIMBAD is operated by CDS; Gaia data are provided by ESA and the Gaia collaboration. The scientific images in this report are processed archive observations. AI-assisted development and writing are documented in the repository's AI-use notes.
