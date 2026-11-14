# Case selection and scientific verification

Owner: Sathvik. Check version: `science-check-1`, run 2026-11-14 ~11:30 CST on branch `codex/sathvik-science`.

Everything below was re-derived from the 183 retained original FITS cutouts in `research/build_data/raw/` (not from earlier summaries). To reproduce:

```bash
.research-venv/bin/python science/check_frames.py
```

```bash
.research-venv/bin/python science/check_registration.py moving_neighbor
```

```bash
.research-venv/bin/python science/check_registration.py fair_comparison
```

Outputs: `science/audit/frames.json` (per-frame facts, no pixels), `science/audit/registration_<case>.json` and `.png`.

## Method

- **Time:** `DATE-AVG` / `MJD-AVG` (mid-exposure) from the IMAGE header. The manifest's `date_utc` is `DATE-OBS` (exposure start, ~1 minute earlier). Pick one convention app-wide; this content uses mid-exposure.
- **Target position:** SIMBAD J2000 position + proper motion + parallax distance, propagated with astropy `apply_space_motion` to each frame's MJD-AVG. Annual parallax and binary orbit not modeled (< 0.1 px).
- **Wavelength:** spectral WCS key `W` evaluated at that position (SIP disabled for the spectral WCS, as in the IRSA tutorial). Not sampled when the position is off the cutout.
- **Quality screen:** circle of radius 2.5 px (~15″) around the predicted position. `flagged` if any flag bit other than `SOURCE`/`FULLSAMPLE` or any non-finite IMAGE/VARIANCE pixel is in the circle; `not_covered` only if the position is off the cutout; otherwise `clear`.

## Agreement with the earlier audit

| Check | Result |
|---|---|
| Wavelength at target, 179 comparable frames | max difference 2.7e-9 µm |
| Target pixel position | max difference 3e-6 px |
| Per-target clear / flagged / not covered | Barnard 0/34/0, Eps Ind B 29/14/1, WISE 0855 21/13/0, RW Aur 1/32/2, R Dra 0/35/1. These match `docs/RESEARCH.md`. |

**Two defects found in the earlier audit logic (route to Sagar so the new processor avoids them):**

1. **Wavelength reported for uncovered positions.** For 4 frames (Eps Ind B 2025-04-25 D1, RW Aur 2025-09-08 D2 and 2026-09-11 D2, R Dra 2025-07-04 D4) the target lies off the cutout, but the old audit still reported a wavelength (WCS extrapolated off the image). The new processor must return `wavelength_um: null` there.
2. **Saturation is not missing coverage.** R Draconis has many non-finite central pixels (saturated; flags OVERFLOW/BLOOM). A naive "too few finite pixels → not covered" rule misreports 29 of 36 R Dra frames as uncovered. Coverage is geometric; non-finite pixels at a covered position are a quality flag.

## fair_comparison — Epsilon Indi B

Pair ranking: of all clear Eps Ind B frame pairs more than 90 days apart, the closest in wavelength relative to bandwidth is the planned pair.

| Ref | frame_key | Release | Mid-exposure UTC | λ at target (µm) | Bandwidth | Screen |
|---|---|---|---|---|---|---|
| A | 2026W18_1A_0516_1_D3 | DR1 | 2026-04-29 12:05:47.874 | 2.32317 | 0.0577 | clear (0/19) |
| B | 2026W39_2A_0597_4_D3 | QR3 | 2026-09-27 07:44:24.312 | 2.32195 | 0.0573 | clear (0/18) |
| C | 2026W18_1A_0516_1_D6 | DR1 | 2026-04-29 12:05:47.874 | 4.93988 | 0.0376 | clear (0/20) |

- **A vs B:** Δλ = 0.0012 µm (2% of bandwidth), 151 days apart. Same detector. Both use pipeline version `l2b-v27`, from different releases (DR1 vs QR3).
- **Runner-up (same release, DR1 only):** 2025W40_1A_0675_3_D2 (2025-10-02, 1.4016 µm) and 2026W17_2A_0355_4_D2 (2026-04-25, 1.4002 µm), Δλ = 0.0014 µm, 205 days. Swap to this pair if the team prefers to avoid the DR1/QR3 caveat.
- **Visual check:** Eps Ind B is an obvious point source at the marker in A, B and C, with peak/MAD of 76, 130 and 118.
- **Registration on a fixed 5″ grid:** 4 control stars. Median control shift ≤ 0.08 px (A↔B) and ≤ 0.25 px (A↔C).
- **Motion:** the marker moves 1.9″ (0.38 grid px) from A to B. **Motion is not visible in this pair**, and the case copy says so.
- **Internal sanity check, not for display:** a crude 2.5 px aperture sum minus an annulus background gives 13.46 vs 13.71 (MJy/sr·px) for A vs B. There is no large change, but this is **not photometry** (aperture smaller than the PSF, no PSF/phase correction, different releases). The case makes no brightness claim.
- **Noted, not claimed:** uneven background toward some image edges, and HALO flags in several *other* Eps Ind B frames. Neither is in the A/B/C apertures. The cause was not established; plausibly scattered light from Eps Ind A, ~6.7′ away.

## moving_neighbor — Barnard's Star

| Ref | frame_key | Release | Mid-exposure UTC | λ at target (µm) | Screen |
|---|---|---|---|---|---|
| A | 2025W35_1A_0008_1_D3 | DR1 | 2025-08-25 00:50:31.845 | 2.00624 | flagged (19/19: OVERFLOW, BLOOM, SUR_ERROR, TRANSIENT) |
| B | 2026W12_1A_0610_2_D3 | DR1 | 2026-03-19 09:06:02.748 | 2.01227 | flagged (20/20) |
| C | 2026W34_1A_0431_1_D3 | QR3 | 2026-08-19 04:57:42.053 | 2.02844 | flagged (19/19) |

- **Why these three:** same detector, three epochs over ~1 year, wavelengths within 0.022 µm. Every Barnard's Star frame is flagged at the star, so no clear option exists.
- **Registration on a fixed north-up 5″ grid, 10 control stars:**
  - Median control shift is ≤ 0.17 px in each axis, with per-star scatter of ~0.3–0.4 px.
  - The catalog marker moves +5.9″ north (A→B) and +10.2″ north (A→C), about 2 grid px.
  - The bright glow visibly shifts north relative to a fixed guide line (`science/audit/registration_moving_neighbor.png`).
- **Not supported:** a proper-motion value. 10–11 non-finite pixels lie within 2 px of the marker in every frame, so the saturated core makes a centroid meaningless.

## WISE 0855 coordinate provenance (for the optional third case and the challenge test)

- **Challenge coordinate:** `08h55m10.831s −07d14m42.53s` (133.795129°, −7.245147°). It matches the catalog propagation to **~2010.5** within 0.4″, i.e. the WISE-discovery-era position.
- **Distance by 2026.0:** the object is **126.7″ (2.1′)** west of that coordinate.
  - A query centered on the challenge coordinate needs a field of view of at least ~4.5′ to contain it.
  - The default 6′ field does. A 2′ field would miss it entirely, even though the search "succeeds".

## Known-covered non-preset coordinate (for the live-query gate)

- **Epsilon Indi A:** RA 330.8400°, Dec −56.7860°, a bright K5V star ~6.7′ from Eps Ind B and not one of the five presets.
- **SIA, radius 0.01°:**
  - `spherex_dr1` returned **355 records** (HTTP 200, 2026-11-14 ~11:31 CST), for example `level2_2025W18_1B_0081_2D6_spx_l2b-v27-2026-196.fits`.
  - `spherex_qr3` returned **HTTP 502 with an HTML body** in the same minute.
- **Expectations:** its frames will be flagged at the star (bright), which is fine for this gate. The gate tests that the coordinate reaches the archive, not that the frames are clean.
- **Observed IRSA behavior at ~11:30 CST:** intermittent `502 Proxy Error` HTML responses, alternating with valid VOTables for the same query. The API must classify these as `UPSTREAM_UNAVAILABLE` (and a single-collection failure as `partial`), never as an empty result.
