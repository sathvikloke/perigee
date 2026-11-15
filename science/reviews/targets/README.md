# Five-preset identity and coordinate audit

Reviewer: parallel worker 11. Recorded times, 2026-11-15 UTC: the first source retrieval was at 00:27:04; the review commit `49f4f8c` was at 00:39:45 (18:39:45 CST on 2026-11-14); the provenance-link check was at 00:37. Review only. Products and case texts were not changed. A small candidate patch to `backend/content/targets.json` is in a separate commit and needs Sathvik's approval (§4).

Subject: `backend/content/targets.json` (`targets-2026-11-14a`) and the 189 shipped product records under `backend/content/presets/**`, on `claude/perigee-integration` @ `54137e0`.

**Verdict.** All five identities, catalog positions, epochs, proper motions and parallaxes match SIMBAD exactly. The query centers match an independent propagation to within 1e-4″. Every shipped record uses `query_center` as its grid center and the 6′ default field of view. The markers reproduce to within 0.0007 display px.

No catalog discrepancy moves a marker by 0.5 display px or more when the repo's own convention is used. Two things are worth acting on:
- **WISE 0855 provenance label.** It names the wrong paper (row 1).
- **WISE 0855 field star.** A cataloged Gaia DR3 field star lies 4.5–11.8″ from the WISE 0855 marker in the 34 shipped frames (observed 2025-05-05 to 2026-05-11). Propagation predicts a closest approach of 3.2″ at about J2026.735, after the last shipped frame. A spot near the marker therefore does not by itself identify WISE 0855 (row 8). This review does not identify any detection.

One measured offset is just above 0.5 px: Epsilon Indi B, 0.56 px (row 2). It is under a quarter of a native SPHEREx pixel and changes no quality screen.

## 1. Discrepancy table

1 display px = 1.40625″ (6′ grid, 256 px). 1 native SPHEREx px ≈ 6.15″ ≈ 4.4 display px. "Marker impact" is the shift of the catalog-prediction marker over all shipped frames of that preset, or the measured offset where stated.

| # | Preset · field | Repo value | Primary-source value | Delta | Marker impact (display px) | Verdict |
|---|---|---|---|---|---|---|
| 1 | wise_0855 · `catalog_position.astrometry_reference` (and the `marker.source` text in all 34 wise_0855 records) | "CatWISE2020 (2021ApJS..253....7K)" | 2021ApJS..253....7K is Kirkpatrick et al. 2021, *The field substellar mass function based on the full-sky 20 pc census of 525 L, T, and Y dwarfs*. CatWISE2020 is 2021ApJS..253....8M (SIMBAD `ref` table) | Label only | 0 | **Fixed in PR #41** (`a5522ea`): the label was corrected and the 34 records regenerated (`marker.source` only; no numbers change). |
| 2 | epsilon_indi_b · proper motion | Gaia DR3 (3981.977, −2466.832) mas/yr, the same as SIMBAD | Gaia DR3 6412596012146801152 has RUWE 4.30 (unresolved Ba+Bb, 11-year orbit), so its 5-parameter motion is photocentric. Other SIMBAD values: 2016ApJS..224...36K (4003.2, −2490.6); 2018MNRAS.481.3548S (4004.97, −2575.05) | 32 and 111 mas/yr | Other catalog PMs: 0.24 and 0.80 px. **Measured:** the native centroid sits **0.56 ± 0.07 px** (+0.37″ E, −0.70″ N) from the marker, consistently in SWIR and MWIR and in 2025 and 2026 (32 frames, Gaia-registered) | Real, but 0.13 native px. The screen (r = 2.5 native px) is unaffected. **Keep the values**: a better prediction needs an orbit model, which is out of scope. The existing note ("binary orbital motion ... not modeled") covers it. |
| 3 | barnards_star · propagation convention | SIMBAD J2000 position, propagated *with* RV −110.11 km/s | SIMBAD's J2000 position equals Gaia DR3 at 2016.0 propagated *without* RV (agrees to 6e-10″). Gaia DR3 4472832130942575872 propagated from 2016.0 with RV is the self-consistent prediction | 0.37″ north at 2026 (perspective acceleration applied over 2000–2016 although SIMBAD did not) | 0.26–0.27 px | Below threshold. The Barnard review saw this as "within 0.32 px". No change. If it is ever rebuilt, propagate from Gaia's 2016.0 epoch. |
| 4 | rw_aurigae · identity and position | "V* RW Aur": Hipparcos (2007A&A...474..653V) system position and PM | Gaia DR3 resolves A (156430817820015232: G 13.04, RUWE 16.4) and B (156430822114424576: G 12.18, 1.49″ at PA ≈ 254°) | A: 0.18″. B: 1.65″ | A: 0.13 px. B: 1.17 px. **Measured** native centroid: 0.56 ± 0.11 px toward the west, as expected for an A+B blend | Expected: SPHEREx sees the blended pair, and `object_type` already says "system". No change. |
| 5 | r_draconis · `radial_velocity_kms` | `null` in targets.json; −132.8 in manifest.json (used for the markers) | SIMBAD −132.8 km/s (1953GCRV, quality E) | Field inconsistency | < 1e-5 px (parallax 1.25 mas) | Harmless. No change. |
| 6 | wise_0855 · catalog position | SIMBAD, J2000, quality **C**, no stated error | CatWISE2020 (IRSA) splits the object into 3 fast-moving fragments. They lie 0.43, 0.66 and 1.18″ from the repo track at 2015.405. Alternative PM 2019ApJS..240...19K (−8118.9, 679.3) | ≤ 1.2″ (fragments); ≤ 0.2″ (PM) | PM: ≤ 0.15 px. Fragments: ≤ 0.84 px at 2015.4 (coarse, apparent-motion fits) | Consistent. No change. |
| 7 | wise_0855 · `challenge_supplied_coordinate` | 133.795129°, −7.245147° ("08h55m10.831s −07d14m42.53s") | Challenge page: "08h55m10.831s, declination -7d14m42.53s" (no epoch given) | 0 (value). The best match on the catalog track is epoch 2010.45 (0.20″). It is 0.44″ from the track at 2010.5 | 121–130″ from the shipped markers (86–92 px), 126.7″ from `query_center`. A field of at least 4.3′ holds the object at the shipped epochs; the repo says "~4.5′" | Correct, and correctly kept separate from `query_center`. No change. |
| 8 | wise_0855 · interpretation (new) | `quality_summary` says passing the screen ≠ detection | Gaia DR3 5756956644387831296 (G 16.3, nearly static) is 4.5–11.8″ from the WISE 0855 marker in the shipped frames: 7.9″ at 2025.85 and 4.5″ at 2026.36. It reaches a minimum of **3.2″ at ≈ 2026.73** (QR3) | Not a catalog error | My centroid routine locked onto this star in 11 of 34 frames. The offsets track the Gaia position (for example −4.94/+2.83 px measured vs −4.99/+2.71 px predicted) | **Applied in PR #41** (`a5522ea`) with conservative wording. The note gives the 4.5–11.8″ range over the shipped frames (2025-05-05 to 2026-05-11) and says that a spot near the marker does not by itself identify WISE 0855. The predicted 3.2″ approach falls after the shipped frames, so it matters for live searches. |

Also confirmed, with no discrepancy:

- **Text claims in targets.json:**
  - Barnard's Star moves 10.39″/yr and is 4.51′ north at 2026.0.
  - Epsilon Indi B is 12.05 ly away and 2.03′ from J2000 at 2026.0.
  - WISE 0855 is 7.43 ly away and moves 8.15″/yr. The text says "about 8.1"; "about 8.2" would be the rounded value. This is cosmetic and not patched.
  - RW Aur and R Dra moved 0.56″ between J2000 and 2026.0.
  - Annual parallax is not modeled. Over the shipped frames it is at most 0.39 px (Barnard's Star), 0.32 px (WISE 0855) and 0.19 px (Eps Ind B), so the "< 0.6″" statement holds.
  - Eps Ind A is 6.71′ away: already verified in `science/reviews/epsilon/`, not redone.
- **SIMBAD names resolve:**
  - All five `simbad_name` values resolve on the CfA mirror.
  - The WISE discovery name "WISE J085510.83-071442.5" resolves to the same object as "WISEA J085510.74-071442.5".
  - Spectral types match SIMBAD: M4V, T1V+T6V, Y2, K1/5e+K5e, and M4.5-6+e.
- **Provenance links:** the `source_url` Sesame links on cds.unistra.fr still respond. They redirect (HTTP 302) to the IDIA mirror and return XML, checked at 00:37 UTC.

## 2. What was already verified elsewhere (reused, not redone)

- `science/reviews/acceptance/`:
  - The markers equal an astropy `apply_space_motion` prediction from the manifest astrometry for all 189 records.
  - The Gaia registration of the images.
  - Its stated limitation was "shared astrometry: a catalog error would go unnoticed". Rows 1–8 address that.
- `science/reviews/barnard/`: Barnard's Star's own Gaia DR3 row agrees to within 0.32 px. Row 3 explains why.
- `science/reviews/epsilon/`:
  - Eps Ind A lies at 6.71′, outside the field.
  - Its PNG glow proxy is within 0.25 px of the marker in frames A and B. My native centroids for those two frames are (−0.09, +0.20) and (−0.17, −0.63) px, Gaia-corrected.

## 3. Method

- `check_targets.py` (Python stdlib only) reads targets.json, manifest.json and every product record. It compares them with the cached source snapshots in `sources/`. It recomputes:
  - the query centers, with a rigorous linear space-motion propagation, written independently;
  - every marker;
  - the marker shift under each alternative astrometry;
  - annual parallax, using a low-precision solar ephemeris;
  - the challenge-coordinate geometry.

  Output: `results.json`.
- `check_centroids.py` (astropy) reads the original FITS read-only. For each covered frame:
  - It centroids the target near its predicted native pixel and registers the header WCS per frame with Gaia DR3 field stars. It imports the centroid and Gaia helpers from `science/reviews/acceptance/check_acceptance.py`.
  - It reports (east, north) offsets.

  Barnard's Star and R Dra are mostly saturated: 9 and 0 frames could be centroided. Output: `centroids.json`.

```bash
python3 science/reviews/targets/check_targets.py
~/Library/Python/3.9/bin/uv venv --python /Users/sathvikloke/.local/bin/python3.12 .venv
~/Library/Python/3.9/bin/uv pip install -p .venv/bin/python astropy numpy pillow
.venv/bin/python science/reviews/targets/check_centroids.py \
  --data-root "/Users/sathvikloke/Documents/ChatGPT/NASA Space Comp/research/build_data"
```

## 4. Candidate patch: superseded by PR #41

> **Status, 2026-11-15:** the reference-label correction was applied in PR #41 (`a5522ea`), on the release coordinator's authorization. That PR used more conservative field-star wording than the candidate below. It also **regenerated** the 34 wise_0855 records through `tools.ingest.ingest`, so `marker.source` no longer carries the wrong label: all 68 PNGs are byte-identical and the only JSON change is `marker.source`. The candidate commit `487bf8a` was not merged. The original candidate is described below for the record.

`backend/content/targets.json` only:
- `content_version` goes from `targets-2026-11-14a` to `targets-2026-11-14b`.
- wise_0855 `astrometry_reference` becomes "Kirkpatrick et al. 2021, 20 pc census (2021ApJS..253....7K)".
- One sentence is added to the wise_0855 `quality_summary` about the Gaia DR3 field star. The candidate said a nearby spot is "likely" that star; PR #41 instead says the star "can fall in the marker's neighbourhood" and that a spot near the marker "does not by itself identify WISE 0855".

**Effect on shipped products.**
- No coordinates, query centers or markers change, and no product needs rebuilding for correctness.
- The 34 wise_0855 records still say "CatWISE2020 (2021ApJS..253....7K)" in `marker.source` until the next rebuild, which would pick up the corrected label. Text only.
- The served `/api/v1/presets` descriptor changes: tests compare it verbatim with the file, so they follow automatically.

Changes to coordinate values were considered and **not recommended**:
- Eps Ind B (row 2) would need an orbit model.
- For Barnard's Star (row 3), switching to a 2016.0 Gaia epoch would move every marker by about 0.27 px. That changes shipped products for no visible benefit.

## 5. Sources (retrieved 2026-11-15 UTC; raw responses in `sources/`)

- **SIMBAD TAP, CfA mirror:** `https://simbad.cfa.harvard.edu/simbad/sim-tap/sync`
  - `basic`: 00:27:13
  - `ident`: 00:28:10
  - `mesPM`: 00:28:32
  - `ref` and position errors: 00:29:31
- **SIMBAD object page:** `https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=NAME%20Barnard%27s%20star&output.format=ASCII`, 00:27:04. It confirms "Coordinates(ICRS,ep=J2000,eq=2000)".
- **Gaia DR3 TAP:** `https://gea.esac.esa.int/tap-server/tap/sync`, table `gaiadr3.gaia_source`:
  - by source_id: 00:28:53
  - RW Aur cone, 0.003°: 00:28:56
  - Eps Ind B cone, 0.002°: 00:29:00
- **Gaia field-star lists:** the cached `science/reviews/acceptance/gaia/*.csv` (same service).
- **CatWISE2020 via IRSA Gator:** `https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=catwise_2020&spatial=cone&objstr=133.78387+-7.24417&radius=20&outfmt=1`, 00:32:42. IRSA TAP timed out.
- **Challenge statement:** `https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/`, 00:29:50. The WISE 0855 coordinate was read from the page.

## 6. Limitations

- The centroids are a consistency check, not astrometry:
  - native pixels are 6.1″;
  - the centroid is a 5×5 first moment on an undersampled PSF;
  - the WCS correction uses 1–9 Gaia stars per frame.

  Medians over many frames are meaningful at about 0.1 px; single frames are not.
- I did not use an Eps Ind Ba/Bb orbit (for example, published dynamical-mass astrometry), so row 2 attributes the offset to the binary as the most plausible cause. It is not proven.
- At SWIR wavelengths, WISE 0855 itself is far below SPHEREx sensitivity. I did not test whether it is detected in the MWIR frames (≈ 4–5 µm). Row 8 shows only that, in the frames where my centroid routine found a source near the marker, that source's position matched this cataloged star. That is consistent with the star, but it does not show what dominates the light there.
- SIMBAD gives no position uncertainty for WISE 0855 (quality C). The 2010.45 epoch match in row 7 is consistent with, but does not prove, the challenge coordinate's epoch.
- I did not check the live `/api/v1/frame` path or frontend rendering of the marker.
