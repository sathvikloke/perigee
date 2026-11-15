"""N2 overnight controls A-E: reproducible counterexample experiments.

One command regenerates every table, figure and the manifest:

    .venv/bin/python science/reviews/overnight-controls/run_controls.py \
        --data-root "/path/to/research/build_data" \
        --out science/reviews/overnight-controls/results

The output directory must be absent or empty (a clean run). Source frames are
read only: shipped FrameRecords/PNGs under backend/content/presets, the case
files, the cached Gaia DR3 cones and the retained raw FITS. Nothing outside
--out is written.

Controls (see README.md for question, invariant, result, lesson and limit):
  A  stretch: P/Q per-frame vs one explicit shared stretch (grey-level mapping)
  B  flagged features: P/Q detector pixel (1709, 1364) and the P-only feature
  C  wavelength/time/provenance table for Epsilon Indi B A/B/C and WISE P/Q/R
  D  positive visual control: Barnard's Star glow proxies vs field stars
  E  information-removal matrix: which questions each representation answers

None of this is photometry, astrometry, a detection test or a learner study.
Deterministic mappings are reported with tolerances, not statistics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image, ImageDraw, ImageFont

warnings.simplefilter("ignore")
from astropy import log as _astropy_log  # noqa: E402

_astropy_log.setLevel("ERROR")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from backend.data import process as proc  # noqa: E402
from backend.data.process import (  # noqa: E402
    FrameInput,
    display_limits_from_values,
    flag_bit_names,
    grid_wcs,
    process_frame,
    sky_to_display_px,
)
from tools.ingest.ingest import target_input  # noqa: E402

PRESETS = REPO / "backend/content/presets"
WISE_KEYS = {"P": "2025W45_2A_0278_1_D2", "Q": "2025W46_1A_0108_1_D2", "R": "2026W20_1A_0214_1_D2"}
F1_DETECTOR_XY = (1709, 1364)  # P/Q feature, 0-based active detector pixel (WCS key A)
BARNARD_GAIA_ID = "4472832130942575872"
INFORMATIONAL = set(proc.INFORMATIONAL_FLAGS)
PROBES_MJY_SR = [0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
PROBE_BIN_MJY_SR = 0.02  # half-width of the empirical value bin used on real pixels


# ============================================================== input tracking
class Inputs:
    """Every file read is hashed and listed in manifest.json."""

    def __init__(self, data_root: Path):
        self.data_root = data_root.resolve()
        self.items: dict = {}

    def label(self, p: Path) -> str:
        p = p.resolve()
        for root, tag in ((self.data_root, "data_root"), (REPO, "repo")):
            try:
                return f"{tag}:{p.relative_to(root)}"
            except ValueError:
                pass
        return str(p)

    def read(self, p: Path) -> bytes:
        b = p.read_bytes()
        self.items[self.label(p)] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
        return b

    def json(self, p: Path):
        return json.loads(self.read(p))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def r(x, n=3):
    if x is None:
        return None
    if isinstance(x, np.ndarray):
        x = x.tolist()
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    x = float(x)
    return None if not math.isfinite(x) else round(x, n)


# ============================================================== frame loading
def manifest_entry(manifest, preset, key):
    obs, det = key.rsplit("_D", 1)
    hits = [e for e in manifest["files"] if e.get("obs_id") == obs and e.get("detector") == int(det)
            and e.get("target_id") == preset and e.get("status") == "downloaded"]
    assert len(hits) == 1, (preset, key, len(hits))
    return hits[0]


def native(hd):
    ih = hd["IMAGE"].header
    return {
        "img": np.asarray(hd["IMAGE"].data, dtype=np.float64),
        "var": np.asarray(hd["VARIANCE"].data, dtype=np.float64),
        "flg": np.asarray(hd["FLAGS"].data).astype(np.int64),
        "names": flag_bit_names(hd["FLAGS"].header),
        "cel": WCS(ih, fobj=hd).celestial,
        # Detector coordinates: key-A LINEAR WCS with SIP removed. (The IMAGE header's
        # SIP terms belong to the celestial solution; all_pix2world on the raw key-A
        # WCS would apply them and shift detector coordinates by ~14-25 px.)
        "det": WCS(proc._without_sip(ih), key="A"),
        "hdr": ih,
        "primary": hd[0].header,
        "crpix_a": (float(ih["CRPIX1A"]), float(ih["CRPIX2A"])),
    }


def load_frame(ctx, preset, subdir, key):
    d = PRESETS / preset / subdir
    rec = ctx.inp.json(d / f"{key}.json")
    png_b = ctx.inp.read(d / f"{key}.png")
    flags_b = ctx.inp.read(d / f"{key}.flags.png")
    ent = manifest_entry(ctx.manifest, preset, key)
    raw = ctx.inp.read(ctx.data_root / ent["file"])
    hd = fits.open(io.BytesIO(raw), memmap=False)
    la = np.array(Image.open(io.BytesIO(png_b)).convert("LA"))
    return {
        "key": key, "preset": preset, "subdir": subdir, "rec": rec, "png_bytes": png_b,
        "gray": la[..., 0], "alpha": la[..., 1],
        "flags_rgba": np.array(Image.open(io.BytesIO(flags_b)).convert("RGBA")),
        "ent": ent, "raw": raw, "hd": hd, "n": native(hd),
        "sha_all_equal": rec["provenance"]["sha256"] == ent["sha256"] == sha256(raw),
    }


def meta_for(ctx, fr, preset, limits=None, basis=None):
    tgt = ctx.targets[preset]
    qc = tgt["query_center"]
    ent = fr["ent"]
    return FrameInput(
        query_ra_deg=qc["ra_deg"], query_dec_deg=qc["dec_deg"],
        fov_arcmin=float(tgt.get("default_fov_arcmin") or 6), target=target_input(tgt),
        source_url=ent["archive_url"], cutout_url=ent["source_url"], observation_id=ent["obs_id"],
        collection_id=ent["collection"], detector=ent["detector"], retrieved_at_utc=ctx.manifest.get("created_utc"),
        retrieved_at_basis="Download-ledger creation time (manifest.json created_utc); per-file retrieval time not recorded.",
        expected_sha256=ent["sha256"], display_limits=limits, display_limits_basis=basis)


def grid_for(ctx, preset):
    tgt = ctx.targets[preset]
    qc = tgt["query_center"]
    size = proc.DEFAULT_GRID_SIZE
    return grid_wcs(qc["ra_deg"], qc["dec_deg"], float(tgt.get("default_fov_arcmin") or 6), size), size


def full_grid(fr, gw, size):
    """Display-oriented (row 0 = north) physical values (image unit) on the fixed
    grid, NaN where the processor leaves the pixel transparent. Same sampling as
    process.py (nearest native pixel through the TAN-SIP WCS)."""
    n = fr["n"]
    img, var = n["img"], n["var"]
    finite = np.isfinite(img) & np.isfinite(var) & (var > 0)
    gy, gx = np.mgrid[0:size, 0:size]
    ra_g, dec_g = gw.wcs_pix2world(gx.ravel().astype(float), gy.ravel().astype(float), 0)
    nxp, nyp = n["cel"].all_world2pix(ra_g, dec_g, 0, quiet=True)
    ix = np.floor(nxp + 0.5).astype(np.int64).reshape(size, size)
    iy = np.floor(nyp + 0.5).astype(np.int64).reshape(size, size)
    ny, nx = img.shape
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    vals = np.full((size, size), np.nan)
    vals[ok] = np.where(finite[iy[ok], ix[ok]], img[iy[ok], ix[ok]], np.nan)
    return np.flipud(vals)


def grey_formula(v, lo, hi, soft):
    """Independent re-implementation of the display mapping (8-bit grey)."""
    t = np.clip((np.asarray(v, dtype=np.float64) - lo) / (hi - lo), 0.0, 1.0)
    return np.round(255.0 * np.arcsinh(t * soft) / np.arcsinh(soft)).astype(np.int64)


def decode_png(b):
    la = np.array(Image.open(io.BytesIO(b)).convert("LA"))
    return la[..., 0], la[..., 1]


def png_has_text_chunks(b: bytes) -> list:
    """Names of ancillary text/metadata chunks in a PNG byte stream."""
    out, i = [], 8
    while i < len(b):
        ln = int.from_bytes(b[i:i + 4], "big")
        typ = b[i + 4:i + 8].decode("latin1")
        if typ in ("tEXt", "zTXt", "iTXt", "eXIf", "tIME"):
            out.append(typ)
        i += 12 + ln
    return out


# ============================================================== shared helpers
def gaia_rows(ctx, name):
    import csv as _csv
    txt = ctx.inp.read(REPO / f"science/reviews/acceptance/gaia/{name}.csv").decode()
    rows = list(_csv.DictReader(io.StringIO(txt)))
    for g in rows:
        for k in ("ra", "dec", "ref_epoch", "phot_g_mean_mag"):
            g[k] = float(g[k])
        for k in ("pmra", "pmdec"):
            g[k] = float(g[k]) if g[k] not in ("", None) else 0.0  # 2-parameter rows: no PM
    return rows


def mjd_to_jyear(mjd):
    return 2000.0 + (mjd - 51544.5) / 365.25


def gaia_at(g, mjd):
    dt = mjd_to_jyear(mjd) - g["ref_epoch"]
    dec = g["dec"] + g["pmdec"] * dt / 3.6e6
    ra = g["ra"] + g["pmra"] * dt / 3.6e6 / math.cos(math.radians(g["dec"]))
    return ra, dec


def sep_arcsec(ra1, dec1, ra2, dec2):
    a1, d1, a2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin((a2 - a1) / 2) ** 2
    return math.degrees(2 * math.asin(min(1.0, math.sqrt(h)))) * 3600.0


def adverse_names(n, v):
    return sorted(nm for b, nm in n["names"].items() if (v >> b) & 1 and nm not in INFORMATIONAL)


def all_names(n, v):
    return sorted(nm for b, nm in n["names"].items() if (v >> b) & 1)


def native_star_centroid(n, x, y, half=2, snr_min=15.0, flag_free=True):
    """Background-subtracted first moment around the local max (native px).
    'Usable' = finite window, SNR >= snr_min, not a single-pixel spike, and (if
    flag_free) no adverse flag in the (2*half+1)^2 window. Returns (cx, cy, snr) or None."""
    img, flg = n["img"], n["flg"]
    ny, nx = img.shape
    ix, iy = int(round(x)), int(round(y))
    if not (half + 6 <= ix < nx - half - 6 and half + 6 <= iy < ny - half - 6):
        return None
    sub = img[iy - 1: iy + 2, ix - 1: ix + 2]
    if not np.isfinite(sub).all():
        return None
    dy, dx = np.unravel_index(np.argmax(sub), sub.shape)
    cx, cy = ix + dx - 1, iy + dy - 1
    w = img[cy - half: cy + half + 1, cx - half: cx + half + 1]
    ring = img[cy - 6: cy + 7, cx - 6: cx + 7]
    if not np.isfinite(w).all():
        return None
    fw = flg[cy - half: cy + half + 1, cx - half: cx + half + 1]
    if flag_free and any(adverse_names(n, int(v)) for v in fw.ravel()):
        return None
    bg = np.nanmedian(ring)
    mad = 1.4826 * np.nanmedian(np.abs(ring - bg)) + 1e-12
    snr = (w.max() - bg) / mad
    nb = sorted(w[half - 1: half + 2, half - 1: half + 2].ravel())[-2]
    if snr < snr_min or (nb - bg) < 0.15 * (w.max() - bg):
        return None
    wt = np.clip(w - bg, 0, None)
    yy, xx = np.mgrid[cy - half: cy + half + 1, cx - half: cx + half + 1]
    return float((wt * xx).sum() / wt.sum()), float((wt * yy).sum() / wt.sum()), float(snr)


def grid_centroid(vals, x, y, half=5, bg_half=12):
    """Background-subtracted first moment on the display grid (physical values);
    returns display coords (pixel centres at i+0.5) or None."""
    size = vals.shape[0]
    ix, iy = int(math.floor(x)), int(math.floor(y))
    if ix - bg_half < 0 or iy - bg_half < 0 or ix + bg_half + 1 > size or iy + bg_half + 1 > size:
        return None
    big = vals[iy - bg_half: iy + bg_half + 1, ix - bg_half: ix + bg_half + 1]
    if not np.isfinite(big).all():
        return None
    bg = np.median(big)
    w = np.clip(vals[iy - half: iy + half + 1, ix - half: ix + half + 1] - bg, 0, None)
    if w.sum() <= 0:
        return None
    yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
    return float((w * (xx + 0.5)).sum() / w.sum()), float((w * (yy + 0.5)).sum() / w.sum())


# ---------------------------------------------------------------- drawing
def font(sz=12, bold=False):
    for p in (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else []) + [
            "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            continue
    return ImageFont.load_default()


BG = (250, 250, 248)
INK = (25, 25, 30)
MUTED = (95, 95, 105)
C_P = (31, 119, 180)
C_Q = (214, 96, 39)
C_SH = (40, 150, 70)
C_MAG = (200, 40, 170)


def grey_rgb(gray, alpha, hole=(70, 120, 210)):
    rgb = np.stack([gray] * 3, -1).astype(np.uint8)
    rgb[alpha == 0] = hole
    return rgb


def overlay(rgb, flags_rgba):
    base = Image.fromarray(rgb).convert("RGBA")
    base.alpha_composite(Image.fromarray(flags_rgba))
    return np.array(base.convert("RGB"))


def save_png(img: Image.Image, path: Path, colors=None):
    if colors:
        img = img.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    img.save(path, optimize=True)


def derived_banner(dr, W, text):
    dr.rectangle([0, 0, W, 22], fill=(40, 40, 48))
    dr.text((8, 4), "DERIVED VIEW (not a source frame) - " + text, fill=(255, 255, 255), font=font(12, True))


# ============================================================== control A
def control_A(ctx):
    preset = "wise_0855"
    gw, size = grid_for(ctx, preset)
    fr = ctx.wise
    renders, gv, repro = {}, {}, {}
    for ref in "PQ":
        pf = process_frame(fr[ref]["raw"], meta_for(ctx, fr[ref], preset))
        gv[ref] = pf.grid_values
        repro[ref] = {"png_bytes_equal_shipped": pf.png_bytes == fr[ref]["png_bytes"],
                      "display_scale_equal_shipped": pf.record["display_scale"] == fr[ref]["rec"]["display_scale"]}
        renders[(ref, "per_frame")] = (pf.png_bytes, pf.record["display_scale"])
    lo, hi = display_limits_from_values([gv["P"], gv["Q"]])
    basis = ("N2 control A: shared asinh stretch, percentiles 1-99.5 of the pooled finite grid pixels "
             "of P and Q (same rule tools/ingest uses for authored cases). Display only; not photometry.")
    for ref in "PQ":
        pf = process_frame(fr[ref]["raw"], meta_for(ctx, fr[ref], preset, limits=(lo, hi), basis=basis))
        renders[(ref, "shared")] = (pf.png_bytes, pf.record["display_scale"])
    names = {}
    for (ref, mode), (b, _) in renders.items():
        nm = f"A_{ref}_{mode}.png"
        (ctx.out / nm).write_bytes(b)
        names[(ref, mode)] = nm

    vals = {ref: full_grid(fr[ref], gw, size) for ref in "PQ"}
    checks, decoded = {}, {}
    for (ref, mode), (b, ds) in renders.items():
        gray, alpha = decode_png(b)
        decoded[(ref, mode)] = (gray, alpha)
        v = vals[ref]
        fin = np.isfinite(v)
        exp = grey_formula(v[fin], ds["low"], ds["high"], ds["asinh_softening"])
        diff = np.abs(gray[fin].astype(np.int64) - exp)
        checks[f"{ref}_{mode}"] = {
            "png": names[(ref, mode)],
            "png_sha256": sha256(b),
            "display_scale": {k: ds[k] for k in ("mode", "method", "asinh_softening", "low", "high", "unit")},
            "finite_display_pixels": int(fin.sum()),
            "alpha_matches_finite_mask": bool(((alpha == 255) == fin).all()),
            "max_abs_grey_minus_formula": int(diff.max()),
            "pixels_differing_from_formula": int((diff > 0).sum()),
            "median_grey": float(np.median(gray[fin])),
            "fraction_white_255": r(float((gray[fin] == 255).mean()), 4),
            "fraction_black_0": r(float((gray[fin] == 0).mean()), 4),
        }

    def g(ref, mode, v):
        ds = renders[(ref, mode)][1]
        return int(grey_formula([v], ds["low"], ds["high"], ds["asinh_softening"])[0])

    probe_rows = []
    for v in PROBES_MJY_SR:
        row = {"value_MJy_sr": v,
               "grey_P_per_frame": g("P", "per_frame", v), "grey_Q_per_frame": g("Q", "per_frame", v),
               "grey_P_shared": g("P", "shared", v), "grey_Q_shared": g("Q", "shared", v)}
        row["per_frame_Q_minus_P"] = row["grey_Q_per_frame"] - row["grey_P_per_frame"]
        row["shared_Q_minus_P"] = row["grey_Q_shared"] - row["grey_P_shared"]
        for ref in "PQ":
            vv = vals[ref]
            m = np.isfinite(vv) & (np.abs(vv - v) <= PROBE_BIN_MJY_SR)
            row[f"n_real_pixels_{ref}"] = int(m.sum())
            for mode in ("per_frame", "shared"):
                gr = decoded[(ref, mode)][0][m]
                ds = renders[(ref, mode)][1]
                fl, fh = grey_formula([v - PROBE_BIN_MJY_SR, v + PROBE_BIN_MJY_SR], ds["low"], ds["high"], ds["asinh_softening"])
                row[f"observed_grey_{ref}_{mode}"] = f"{int(gr.min())}-{int(gr.max())}" if gr.size else ""
                row[f"formula_grey_range_over_bin_{ref}_{mode}"] = f"{int(fl)}-{int(fh)}"
        probe_rows.append(row)

    sweep = np.round(np.arange(0.0, 5.0 + 1e-9, 0.001), 3)
    def curve(ref, mode):
        ds = renders[(ref, mode)][1]
        return grey_formula(sweep, ds["low"], ds["high"], ds["asinh_softening"])
    d_pf = np.abs(curve("P", "per_frame") - curve("Q", "per_frame"))
    d_sh = np.abs(curve("P", "shared") - curve("Q", "shared"))
    phys = {}
    for ref in "PQ":
        v = vals[ref][np.isfinite(vals[ref])]
        phys[ref] = {"median": r(np.median(v), 4), "p16": r(np.percentile(v, 16), 4), "p84": r(np.percentile(v, 84), 4),
                     "unit": "MJy / sr", "n": int(v.size)}
    res = {
        "question": "Does one physical value (MJy/sr) receive different grey levels under the shipped per-frame "
                    "stretches of P and Q, and the same grey level under one shared stretch?",
        "frames": {ref: fr[ref]["key"] for ref in "PQ"},
        "reproduction_of_shipped_per_frame": repro,
        "shared_stretch": {"low": lo, "high": hi, "unit": "MJy / sr", "method": "asinh", "asinh_softening": proc.ASINH_SOFTENING,
                           "rule": "percentiles 1-99.5 of the pooled finite grid pixels of P and Q", "basis": basis},
        "finite_value_treatment": "A display pixel is finite when its native IMAGE value is finite and VARIANCE is finite "
                                  "and > 0 (processor A rule). Non-finite pixels are transparent (alpha 0) and excluded "
                                  "from the percentile stretch and from every statistic here.",
        "mapping_checks": checks,
        "tolerance": "PNG grey must equal round(255*asinh(10*t)/asinh(10)), t = clip((v-low)/(high-low), 0, 1), "
                     "within 0 grey levels (8-bit rounding is part of the formula).",
        "probes": probe_rows,
        "probe_bin_half_width_MJy_sr": PROBE_BIN_MJY_SR,
        "sweep_0_to_5_MJy_sr_step_0.001": {
            "per_frame_max_abs_grey_diff_P_vs_Q": int(d_pf.max()),
            "per_frame_value_at_max_diff_MJy_sr": float(sweep[int(np.argmax(d_pf))]),
            "per_frame_values_with_any_diff_fraction": r(float((d_pf > 0).mean()), 4),
            "shared_max_abs_grey_diff_P_vs_Q": int(d_sh.max()),
        },
        "physical_frame_statistics": phys,
        "physical_median_ratio_Q_over_P": r(phys["Q"]["median"] / phys["P"]["median"], 4),
    }
    ctx.results["A"] = res
    write_csv(ctx.out / "A_stretch_probes.csv", probe_rows)
    figure_A(ctx, decoded, renders, res)
    return res


def figure_A(ctx, decoded, renders, res):
    z = 1.5
    T = int(256 * z)
    pad, top = 14, 30
    W = pad * 3 + 2 * T
    plot_h = 300
    H = top + 2 * (T + 44) + plot_h + 70
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    derived_banner(dr, W, "control A: same P/Q pixels, two display mappings")
    for row, mode in enumerate(("per_frame", "shared")):
        for col, ref in enumerate("PQ"):
            gray, alpha = decoded[(ref, mode)]
            tile = Image.fromarray(grey_rgb(gray, alpha)).resize((T, T), Image.NEAREST)
            x0 = pad + col * (T + pad)
            y0 = top + row * (T + 44) + 34
            im.paste(tile, (x0, y0))
            ds = renders[(ref, mode)][1]
            lab = ("own per-frame stretch (shipped)" if mode == "per_frame" else "one shared P+Q stretch")
            dr.text((x0, y0 - 32), f"{ref}  {ctx.wise[ref]['key']}  - {lab}", fill=INK, font=font(12, True))
            dr.text((x0, y0 - 16), f"asinh(10), low {ds['low']:.3f}  high {ds['high']:.3f} MJy/sr", fill=MUTED, font=font(11))
    # transfer-curve plot
    py0 = top + 2 * (T + 44) + 30
    px0, pw, ph = 60, W - 90, plot_h - 60
    dr.text((pad, py0 - 22), "Display mapping: grey level (display unit, 0-255) vs physical value (MJy/sr)", fill=INK, font=font(12, True))
    dr.rectangle([px0, py0, px0 + pw, py0 + ph], outline=MUTED)
    vmax = 3.5
    def X(v): return px0 + v / vmax * pw
    def Y(gv): return py0 + ph - gv / 255 * ph
    for v in (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5):
        dr.line([X(v), py0 + ph, X(v), py0 + ph + 4], fill=MUTED)
        dr.text((X(v) - 8, py0 + ph + 6), f"{v:g}", fill=MUTED, font=font(10))
    for gv in (0, 64, 128, 192, 255):
        dr.text((px0 - 28, Y(gv) - 6), str(gv), fill=MUTED, font=font(10))
    xs = np.linspace(0, vmax, 400)
    for (ref, mode), col, w in ((("P", "per_frame"), C_P, 2), (("Q", "per_frame"), C_Q, 2), (("P", "shared"), C_SH, 4)):
        ds = renders[(ref, mode)][1]
        gs = grey_formula(xs, ds["low"], ds["high"], ds["asinh_softening"])
        dr.line([(X(a), Y(b)) for a, b in zip(xs, gs)], fill=col, width=w)
    for v in (1.0, 2.0):
        for yy in range(int(py0), int(py0 + ph), 6):
            dr.line([X(v), yy, X(v), yy + 3], fill=(150, 150, 150))
        row = next(p for p in res["probes"] if p["value_MJy_sr"] == v)
        dr.text((X(v) + 4, py0 + ph - 70 + (0 if v == 1.0 else 0)),
                f"{v:g} MJy/sr:\nP own {row['grey_P_per_frame']}\nQ own {row['grey_Q_per_frame']}\nshared {row['grey_P_shared']} = {row['grey_Q_shared']}",
                fill=INK, font=font(10))
    ly = py0 + ph + 24
    for i, (lab, col) in enumerate((("P own stretch", C_P), ("Q own stretch", C_Q), ("shared stretch (P and Q identical)", C_SH))):
        dr.rectangle([px0 + i * 200, ly + 4, px0 + i * 200 + 14, ly + 12], fill=col)
        dr.text((px0 + i * 200 + 18, ly), lab, fill=INK, font=font(11))
    dr.text((pad, H - 22), "Rendering test only: grey levels are display units, not brightness measurements. "
            "Blue = transparent (outside the cutout, or no finite value).", fill=MUTED, font=font(11))
    save_png(im, ctx.out / "A_stretch_pairs.png", colors=160)


# ============================================================== control B
def pixel_report(fr, x, y, gw, size):
    n = fr["n"]
    img, flg = n["img"], n["flg"]
    ny, nx = img.shape
    v = int(flg[y, x])
    ra, dec = n["cel"].all_pix2world([[x, y]], 0)[0]
    dxy = sky_to_display_px(gw, size, ra, dec)
    det = n["det"].wcs_pix2world([[x, y]], 0)[0]
    nb = []
    for yy in range(y - 1, y + 2):
        row = []
        for xx in range(x - 1, x + 2):
            row.append(r(img[yy, xx], 3) if 0 <= xx < nx and 0 <= yy < ny else None)
        nb.append(row)
    flat = [c for rr in nb for c in rr]
    neigh = [c for i, c in enumerate(flat) if i != 4 and c is not None]
    return {
        "native_xy_0based": [x, y],
        "native_xy_fits_1based": [x + 1, y + 1],
        "detector_xy_0based_active": [int(round(det[0])), int(round(det[1]))],
        "ra_deg": float(ra), "dec_deg": float(dec),
        "display_xy": r(dxy, 2),
        "value_MJy_sr": r(img[y, x], 3),
        "variance": r(n["var"][y, x], 5),
        "flags_int": v,
        "flag_bits_set": [b for b in range(31) if (v >> b) & 1],
        "flag_names_all": all_names(n, v),
        "flag_names_adverse": adverse_names(n, v),
        "neighbourhood_3x3_MJy_sr_rows_south_to_north": nb,
        "peak_over_brightest_neighbour": r(img[y, x] / max(neigh), 1) if neigh and max(neigh) > 0 else None,
    }


def det_to_native(fr, dx, dy):
    x, y = fr["n"]["det"].wcs_world2pix([[dx, dy]], 0)[0]
    x, y = int(round(x)), int(round(y))
    ny, nx = fr["n"]["img"].shape
    return (x, y) if (0 <= x < nx and 0 <= y < ny) else None


def detector_range(fr):
    ny, nx = fr["n"]["img"].shape
    a = fr["n"]["det"].wcs_pix2world([[0, 0], [nx - 1, ny - 1]], 0)
    return {"x": [int(round(a[0][0])), int(round(a[1][0]))], "y": [int(round(a[0][1])), int(round(a[1][1]))]}


def sky_to_native_pixel(fr, ra, dec):
    x, y = fr["n"]["cel"].all_world2pix([[ra, dec]], 0)[0]
    ix, iy = int(math.floor(x + 0.5)), int(math.floor(y + 0.5))
    ny, nx = fr["n"]["img"].shape
    return (ix, iy) if (0 <= ix < nx and 0 <= iy < ny) else None


def brightest_within(fr, ra, dec, rad=1.5):
    n = fr["n"]
    x, y = n["cel"].all_world2pix([[ra, dec]], 0)[0]
    ny, nx = n["img"].shape
    best = None
    for yy in range(int(math.floor(y - rad)), int(math.ceil(y + rad)) + 1):
        for xx in range(int(math.floor(x - rad)), int(math.ceil(x + rad)) + 1):
            if 0 <= xx < nx and 0 <= yy < ny and math.hypot(xx - x, yy - y) <= rad and np.isfinite(n["img"][yy, xx]):
                v = float(n["img"][yy, xx])
                if best is None or v > best[0]:
                    best = (v, xx, yy)
    return best


def footprint(vals, x, y, thr, half=15):
    """Display pixels above thr within +-half of (x, y): count and unweighted centroid."""
    size = vals.shape[0]
    ix, iy = int(math.floor(x)), int(math.floor(y))
    y0, y1, x0, x1 = max(0, iy - half), min(size, iy + half + 1), max(0, ix - half), min(size, ix + half + 1)
    sub = vals[y0:y1, x0:x1]
    m = np.isfinite(sub) & (sub > thr)
    if not m.any():
        return None
    yy, xx = np.nonzero(m)
    return {"n_display_px": int(m.sum()), "centroid_display_xy": r([float((xx + x0 + 0.5).mean()), float((yy + y0 + 0.5).mean())], 2)}


def spot_census(ctx, fr, gw, size, gaia):
    """Native local maxima drawn pure white by the frame's own stretch, inside
    the grid, with nearest cached Gaia DR3 (G<17) star."""
    n = fr["n"]
    img = n["img"]
    ny, nx = img.shape
    hi = fr["rec"]["display_scale"]["high"]
    padded = np.pad(img, 1, constant_values=np.nan)
    out = []
    for yy in range(ny):
        for xx in range(nx):
            v = img[yy, xx]
            if not (np.isfinite(v) and v >= hi):
                continue
            nb8 = np.delete(padded[yy:yy + 3, xx:xx + 3].ravel(), 4)
            if np.nanmax(nb8) >= v:
                continue
            ra, dec = n["cel"].all_pix2world([[xx, yy]], 0)[0]
            dx, dy = sky_to_display_px(gw, size, ra, dec)
            if not (0 <= dx < size and 0 <= dy < size):
                continue
            gs = min((sep_arcsec(ra, dec, *gaia_at(g, fr["rec"]["mjd"])), g["source_id"]) for g in gaia)
            det = n["det"].wcs_pix2world([[xx, yy]], 0)[0]
            out.append({"native_xy": [xx, yy], "detector_xy": [int(round(det[0])), int(round(det[1]))],
                        "display_xy": r([dx, dy], 1), "value_MJy_sr": r(v, 2),
                        "adverse_flags": adverse_names(n, int(n["flg"][yy, xx])),
                        "nearest_gaia_sep_arcsec": r(gs[0], 1), "nearest_gaia_id": gs[1]})
    return out


def control_B(ctx):
    preset = "wise_0855"
    gw, size = grid_for(ctx, preset)
    fr = ctx.wise
    gaia = gaia_rows(ctx, "wise_0855")
    vals = {ref: full_grid(fr[ref], gw, size) for ref in "PQR"}
    res = {"question": "Is the dot that 'jumps' between P and Q fixed on the sky (a source) or fixed on the detector? "
                       "Where is the P-only dot on the detector and sky, and is anything there in Q or R?",
           "cutout_origin_convention": {
               "native": "0-based FITS pixel centres of the IMAGE extension of each retained cutout (x = column, y = row; "
                         "row 0 is the first FITS row). FITS 1-based = native + 1.",
               "detector": "WCS key A of the IMAGE header, WCSNAMEA '0-based active pixel coordinates' (LINEAR, CRVAL=0). "
                           "detector = native + 1 - CRPIXnA (CRPIXnA is 1-based, so the offset differs per cutout).",
               "display": "processor A grid: origin at the PNG top-left corner, x right, y down, pixel centres at i+0.5; "
                          "north up, east left; 256 px over 6 arcmin (1.40625 arcsec per display px).",
               "sky": "ICRS RA/Dec from the IMAGE TAN-SIP WCS at the native pixel centre.",
           },
           "frames": {}}
    for ref in "PQR":
        n = fr[ref]["n"]
        res["frames"][ref] = {"frame_key": fr[ref]["key"], "CRPIX1A": n["crpix_a"][0], "CRPIX2A": n["crpix_a"][1],
                              "native_shape_yx": list(n["img"].shape), "detector_range_covered": detector_range(fr[ref]),
                              "display_high_MJy_sr": r(fr[ref]["rec"]["display_scale"]["high"], 4)}
    census = {ref: spot_census(ctx, fr[ref], gw, size, gaia) for ref in "PQR"}
    res["spot_census"] = {"rule": "native local maximum >= the frame's own display_scale.high (drawn white), inside the grid; "
                                  "nearest star from the cached Gaia DR3 G<17 cone (science/reviews/acceptance/gaia/wise_0855.csv)",
                          "spots": census,
                          "unmatched_adverse_over_9arcsec": {ref: [s for s in census[ref] if s["adverse_flags"] and s["nearest_gaia_sep_arcsec"] > 9.0] for ref in "PQR"}}

    # ---------- F1: the P/Q detector pixel
    f1 = {"detector_xy": list(F1_DETECTOR_XY), "per_frame": {}}
    for ref in "PQR":
        nat = det_to_native(fr[ref], *F1_DETECTOR_XY)
        if nat is None:
            f1["per_frame"][ref] = {"covered_by_cutout": False, "detector_range_covered": detector_range(fr[ref])}
            continue
        rep = pixel_report(fr[ref], nat[0], nat[1], gw, size)
        rep["covered_by_cutout"] = True
        rep["in_spot_census"] = any(s["detector_xy"] == list(F1_DETECTOR_XY) for s in census[ref])
        f1["per_frame"][ref] = rep
    p, q = f1["per_frame"]["P"], f1["per_frame"]["Q"]
    f1_sep = sep_arcsec(p["ra_deg"], p["dec_deg"], q["ra_deg"], q["dec_deg"])
    f1_dd = [q["display_xy"][0] - p["display_xy"][0], q["display_xy"][1] - p["display_xy"][1]]
    fp = {ref: footprint(vals[ref], *f1["per_frame"][ref]["display_xy"], thr=0.5 * f1["per_frame"][ref]["value_MJy_sr"]) for ref in "PQ"}
    obs_dd = [fp["Q"]["centroid_display_xy"][0] - fp["P"]["centroid_display_xy"][0],
              fp["Q"]["centroid_display_xy"][1] - fp["P"]["centroid_display_xy"][1]]
    f1["apparent_shift_P_to_Q"] = {
        "same_detector_pixel_sky_separation_arcsec": r(f1_sep, 2),
        "same_detector_pixel_display_delta_xy": r(f1_dd, 2),
        "same_detector_pixel_display_distance_px": r(math.hypot(*f1_dd), 2),
        "observed_display_footprint": fp,
        "observed_footprint_centroid_delta_xy": r(obs_dd, 2),
        "observed_footprint_centroid_distance_px": r(math.hypot(*obs_dd), 2),
        "observed_minus_detector_fixed_prediction_px": r(math.hypot(obs_dd[0] - f1_dd[0], obs_dd[1] - f1_dd[1]), 2),
        "tolerance_note": "Nearest-neighbour resampling places each native pixel (~4.4 display px) as a block whose "
                          "edges are quantized to whole display px, so the footprint centroid can differ from the native "
                          "pixel centre by up to ~0.5 display px per axis per frame.",
        "footprint_threshold": "display pixels above half of the feature's native peak value in that frame",
    }
    # what is at F1's P sky position in Q and R
    sky_chk = {}
    for ref in "QR":
        b = brightest_within(fr[ref], p["ra_deg"], p["dec_deg"])
        nat = sky_to_native_pixel(fr[ref], p["ra_deg"], p["dec_deg"])
        sky_chk[ref] = {"brightest_within_1.5_native_px_MJy_sr": r(b[0], 3) if b else None,
                        "containing_native_pixel": list(nat) if nat else None,
                        "containing_pixel_value_MJy_sr": r(fr[ref]["n"]["img"][nat[1], nat[0]], 3) if nat else None,
                        "containing_detector_xy": (lambda d: [int(round(d[0])), int(round(d[1]))])(fr[ref]["n"]["det"].wcs_pix2world([list(nat)], 0)[0]) if nat else None,
                        "adverse_flags_at_containing_pixel": adverse_names(fr[ref]["n"], int(fr[ref]["n"]["flg"][nat[1], nat[0]])) if nat else None}
    f1["at_P_sky_position_in_other_frames"] = sky_chk

    # usable field sources P vs Q (strict tier = headline; relaxed tier = sensitivity)
    def field_sources(snr_min, flag_free):
        stars = []
        for g in gaia:
            row = {"gaia_dr3": g["source_id"], "G": r(g["phot_g_mean_mag"], 2)}
            ok = True
            for ref in "PQ":
                n = fr[ref]["n"]
                ra, dec = gaia_at(g, fr[ref]["rec"]["mjd"])
                ex, ey = n["cel"].all_world2pix([[ra, dec]], 0)[0]
                c = native_star_centroid(n, ex, ey, snr_min=snr_min, flag_free=flag_free)
                if c is None or math.hypot(c[0] - ex, c[1] - ey) > 1.0:
                    ok = False
                    break
                mra, mdec = n["cel"].all_pix2world([[c[0], c[1]]], 0)[0]
                det = n["det"].wcs_pix2world([[c[0], c[1]]], 0)[0]
                dxy = sky_to_display_px(gw, size, mra, mdec)
                gc = grid_centroid(vals[ref], *sky_to_display_px(gw, size, ra, dec))
                row[ref] = {"native_centroid": r(c[:2], 3), "snr": r(c[2], 1), "ra_deg": float(mra), "dec_deg": float(mdec),
                            "detector_xy": r(det, 3), "display_xy_from_native": r(dxy, 3),
                            "display_grid_centroid": r(gc, 3) if gc else None}
            if not ok:
                continue
            row["sky_shift_arcsec"] = r(sep_arcsec(row["P"]["ra_deg"], row["P"]["dec_deg"], row["Q"]["ra_deg"], row["Q"]["dec_deg"]), 2)
            row["detector_shift_px"] = r([row["Q"]["detector_xy"][0] - row["P"]["detector_xy"][0],
                                          row["Q"]["detector_xy"][1] - row["P"]["detector_xy"][1]], 3)
            if row["P"]["display_grid_centroid"] and row["Q"]["display_grid_centroid"]:
                dd = [row["Q"]["display_grid_centroid"][0] - row["P"]["display_grid_centroid"][0],
                      row["Q"]["display_grid_centroid"][1] - row["P"]["display_grid_centroid"][1]]
                row["display_grid_shift_px"] = r(math.hypot(*dd), 2)
            stars.append(row)
        return stars

    relaxed = field_sources(8.0, False)
    stars = field_sources(15.0, True)
    sky = [s["sky_shift_arcsec"] for s in stars]
    dsh = [s["display_grid_shift_px"] for s in stars if "display_grid_shift_px" in s]
    detsh = np.array([s["detector_shift_px"] for s in stars]) if stars else np.zeros((0, 2))
    f1["usable_field_sources_P_Q"] = {
        "selection": "cached Gaia DR3 G<17 stars whose native centroid in both P and Q is finite, SNR >= 15 (MAD), "
                     "not a single-pixel spike, free of adverse flags in the 5x5 window, and within 1 native px of the "
                     "propagated Gaia position. Positions measured with each frame's own header WCS.",
        "n": len(stars),
        "sky_shift_arcsec": {"median": r(np.median(sky), 2) if sky else None, "max": r(max(sky), 2) if sky else None},
        "display_grid_shift_px": {"median": r(np.median(dsh), 2) if dsh else None, "max": r(max(dsh), 2) if dsh else None, "n": len(dsh)},
        "detector_shift_px_median_xy": r(np.median(detsh, 0), 3) if len(stars) else None,
        "stars": stars,
        "relaxed_tier_sensitivity": {
            "selection": "same, but SNR >= 8 and adverse flags allowed in the window",
            "n": len(relaxed),
            "sky_shift_arcsec_median": r(np.median([s_["sky_shift_arcsec"] for s_ in relaxed]), 2) if relaxed else None,
            "sky_shift_arcsec_max": r(max(s_["sky_shift_arcsec"] for s_ in relaxed), 2) if relaxed else None,
            "detector_shift_px_median_xy": r(np.median([s_["detector_shift_px"] for s_ in relaxed], 0), 3) if relaxed else None,
            "per_star": [{"gaia_dr3": s_["gaia_dr3"], "G": s_["G"], "sky_shift_arcsec": s_["sky_shift_arcsec"],
                          "detector_shift_px": s_["detector_shift_px"]} for s_ in relaxed],
        },
    }
    # Non-tautological check: the stars' measured detector shift predicts how far a
    # detector-fixed pixel should appear to move on the sky (uses P's WCS only).
    if len(stars):
        sdx, sdy = np.median(detsh, 0)
        nx0, ny0 = f1["per_frame"]["P"]["native_xy_0based"]
        (ra_a, de_a), (ra_b, de_b) = fr["P"]["n"]["cel"].all_pix2world([[nx0, ny0], [nx0 - sdx, ny0 - sdy]], 0)
        pred = sep_arcsec(ra_a, de_a, ra_b, de_b)
        f1["star_implied_prediction"] = {
            "method": "A sky-fixed star moves by s detector px (median of usable stars, P->Q). A detector-fixed pixel D then "
                      "samples in Q the sky that detector position D - s sampled in P, so it should appear displaced by "
                      "sep(sky_P(D), sky_P(D - s)) relative to the stars. Uses P's WCS and the star centroids only.",
            "star_median_detector_shift_px": r([sdx, sdy], 3),
            "predicted_sky_shift_arcsec": r(pred, 2),
            "measured_same_pixel_sky_shift_arcsec": r(f1_sep, 2),
            "difference_arcsec": r(abs(pred - f1_sep), 2),
        }
    f1["two_reference_frames"] = {
        "on_sky_grid": f"feature moves {r(f1_sep, 2)} arcsec; usable field stars move median {f1['usable_field_sources_P_Q']['sky_shift_arcsec']['median']} arcsec",
        "on_detector": f"feature stays at detector pixel {list(F1_DETECTOR_XY)} (shift 0); usable field stars shift by median "
                       f"{f1['usable_field_sources_P_Q']['detector_shift_px_median_xy']} detector px",
    }
    f1["R_note"] = ("R's cutout covers a different part of the detector (see detector_range_covered), so R cannot test "
                    "whether detector pixel (1709, 1364) is elevated in May 2026; R only shows the same SKY position.")
    res["F1_PQ_detector_pixel"] = f1

    # ---------- F2: the P-only flagged feature (from the census, not hard-coded)
    cand = [s for s in res["spot_census"]["unmatched_adverse_over_9arcsec"]["P"] if s["detector_xy"] != list(F1_DETECTOR_XY)]
    f2 = {"selection": "P census spots with adverse flags and no cached Gaia DR3 star within 9 arcsec, excluding F1",
          "n_candidates": len(cand)}
    if cand:
        c = max(cand, key=lambda s: s["value_MJy_sr"])
        rep = pixel_report(fr["P"], c["native_xy"][0], c["native_xy"][1], gw, size)
        f2["P"] = rep
        f2["P_display_footprint"] = footprint(vals["P"], *rep["display_xy"], thr=0.5 * rep["value_MJy_sr"])
        others = {}
        for ref in "QR":
            o = {}
            nat = det_to_native(fr[ref], *rep["detector_xy_0based_active"])
            if nat is None:
                o["same_detector_pixel"] = {"covered_by_cutout": False, "detector_range_covered": detector_range(fr[ref])}
            else:
                pr = pixel_report(fr[ref], nat[0], nat[1], gw, size)
                o["same_detector_pixel"] = {"covered_by_cutout": True, **{k: pr[k] for k in (
                    "native_xy_0based", "value_MJy_sr", "flag_names_adverse", "display_xy", "peak_over_brightest_neighbour")}}
            b = brightest_within(fr[ref], rep["ra_deg"], rep["dec_deg"])
            nat2 = sky_to_native_pixel(fr[ref], rep["ra_deg"], rep["dec_deg"])
            o["same_sky_position"] = {"brightest_within_1.5_native_px_MJy_sr": r(b[0], 3) if b else None,
                                      "containing_native_pixel": list(nat2) if nat2 else None,
                                      "containing_pixel_value_MJy_sr": r(fr[ref]["n"]["img"][nat2[1], nat2[0]], 3) if nat2 else None,
                                      "adverse_flags_at_containing_pixel": adverse_names(fr[ref]["n"], int(fr[ref]["n"]["flg"][nat2[1], nat2[0]])) if nat2 else None}
            others[ref] = o
        f2["other_frames"] = others
        vb = vals["P"]
        f2["P_background_median_MJy_sr"] = r(np.nanmedian(vb), 3)
    res["F2_P_only_feature"] = f2

    # flag meanings from the FITS header
    used = set()
    for ref in "PQR":
        for s in census[ref]:
            used |= set(s["adverse_flags"])
    for k in ("F1_PQ_detector_pixel",):
        for ref, rep in res[k]["per_frame"].items():
            used |= set(rep.get("flag_names_all", []))
    if "P" in f2:
        used |= set(f2["P"]["flag_names_all"])
    fh = fr["P"]["hd"]["FLAGS"].header
    res["flag_meanings_from_FITS_header_MSKD"] = {
        str(fh[k]).strip(): str(fh.get("MSKD" + k[4:], "")).strip() for k in fh.keys()
        if k.startswith("MSKN") and str(fh[k]).strip() in used}
    ctx.results["B"] = res
    rows = []
    for ref, rep in f1["per_frame"].items():
        rows.append({"feature": "F1", "frame": ref, "covered": rep["covered_by_cutout"],
                     "native_xy": rep.get("native_xy_0based"), "detector_xy": rep.get("detector_xy_0based_active"),
                     "ra_deg": r(rep.get("ra_deg"), 6), "dec_deg": r(rep.get("dec_deg"), 6), "display_xy": rep.get("display_xy"),
                     "value_MJy_sr": rep.get("value_MJy_sr"), "flags_adverse": "|".join(rep.get("flag_names_adverse", [])),
                     "peak_over_brightest_neighbour": rep.get("peak_over_brightest_neighbour")})
    if "P" in f2:
        rep = f2["P"]
        rows.append({"feature": "F2", "frame": "P", "covered": True, "native_xy": rep["native_xy_0based"],
                     "detector_xy": rep["detector_xy_0based_active"], "ra_deg": r(rep["ra_deg"], 6), "dec_deg": r(rep["dec_deg"], 6),
                     "display_xy": rep["display_xy"], "value_MJy_sr": rep["value_MJy_sr"],
                     "flags_adverse": "|".join(rep["flag_names_adverse"]), "peak_over_brightest_neighbour": rep["peak_over_brightest_neighbour"]})
        for ref, o in f2["other_frames"].items():
            sd = o["same_detector_pixel"]
            rows.append({"feature": "F2 same detector px", "frame": ref, "covered": sd["covered_by_cutout"],
                         "native_xy": sd.get("native_xy_0based"), "detector_xy": rep["detector_xy_0based_active"],
                         "ra_deg": "", "dec_deg": "", "display_xy": sd.get("display_xy"), "value_MJy_sr": sd.get("value_MJy_sr"),
                         "flags_adverse": "|".join(sd.get("flag_names_adverse", []) or []), "peak_over_brightest_neighbour": sd.get("peak_over_brightest_neighbour")})
    write_csv(ctx.out / "B_features.csv", rows)
    write_csv(ctx.out / "B_field_sources.csv", [
        {"gaia_dr3": s["gaia_dr3"], "G": s["G"], "snr_P": s["P"]["snr"], "snr_Q": s["Q"]["snr"],
         "sky_shift_arcsec": s["sky_shift_arcsec"], "detector_shift_dx": s["detector_shift_px"][0],
         "detector_shift_dy": s["detector_shift_px"][1], "display_grid_shift_px": s.get("display_grid_shift_px")} for s in stars])
    figure_B(ctx, vals, res)
    return res


def figure_B(ctx, vals, res):
    fr = ctx.wise
    f1, f2 = res["F1_PQ_detector_pixel"], res["F2_P_only_feature"]
    half, z = 36, 3
    T = 2 * half * z
    pad, lab = 12, 34
    W = pad + 3 * (T + pad)
    rows = 4
    H = 26 + rows * (T + lab + 8) + 60
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    derived_banner(dr, W, "control B: flagged features on sky grid and detector")
    pP, pQ = f1["per_frame"]["P"]["display_xy"], f1["per_frame"]["Q"]["display_xy"]
    cx, cy = int(round((pP[0] + pQ[0]) / 2)), int(round((pP[1] + pQ[1]) / 2))
    stars = f1["usable_field_sources_P_Q"]["stars"]

    def tile_sky(ref, cx, cy, flags):
        g, a = fr[ref]["gray"], fr[ref]["alpha"]
        rgb = grey_rgb(g, a)
        if flags:
            rgb = overlay(rgb, fr[ref]["flags_rgba"])
        pad_rgb = np.pad(rgb, ((half, half), (half, half), (0, 0)), constant_values=40)
        crop = pad_rgb[cy: cy + 2 * half, cx: cx + 2 * half]
        return Image.fromarray(crop).resize((T, T), Image.NEAREST)

    def mark(x0, y0, cx, cy, x, y, col, rad=9, cross=True):
        X, Y = x0 + (x - (cx - half)) * z, y0 + (y - (cy - half)) * z
        if cross:
            dr.line([X - rad, Y, X - 3, Y], fill=col, width=2); dr.line([X + 3, Y, X + rad, Y], fill=col, width=2)
            dr.line([X, Y - rad, X, Y - 3], fill=col, width=2); dr.line([X, Y + 3, X, Y + rad], fill=col, width=2)
        else:
            dr.ellipse([X - rad, Y - rad, X + rad, Y + rad], outline=col, width=2)

    y = 26
    titles = ["F1, sky grid (shipped PNG, own stretch). Cyan + = detector pixel (1709,1364) in P; orange + = same pixel in Q",
              "F1, same crops + shipped flag overlay (red = adverse flag)",
              "F1, detector frame: native cutout pixels at detector x,y (own stretch). Box = (1709,1364); green = usable stars"]
    for row in range(3):
        dr.text((pad, y), titles[row], fill=INK, font=font(11, True))
        for col, ref in enumerate("PQR"):
            x0, y0 = pad + col * (T + pad), y + lab
            rec = fr[ref]["rec"]
            dr.text((x0, y + 16), f"{ref} {fr[ref]['key']}  {rec['observed_at_utc'][:10]}", fill=MUTED, font=font(10))
            if row < 2:
                im.paste(tile_sky(ref, cx, cy, flags=row == 1), (x0, y0))
                mark(x0, y0, cx, cy, *pP, (0, 200, 230))
                mark(x0, y0, cx, cy, *pQ, (255, 140, 0))
                for s in stars:
                    if ref in "PQ":
                        sx, sy = s[ref]["display_xy_from_native"]
                        if abs(sx - cx) < half and abs(sy - cy) < half:
                            mark(x0, y0, cx, cy, sx, sy, (40, 170, 60), rad=7, cross=False)
            else:
                rep = f1["per_frame"][ref]
                if not rep["covered_by_cutout"]:
                    dr.rectangle([x0, y0, x0 + T, y0 + T], fill=(225, 225, 225))
                    rng = rep["detector_range_covered"]
                    dr.text((x0 + 8, y0 + T / 2 - 20), f"detector pixel (1709,1364)\nnot in this cutout\n(covers x {rng['x'][0]}-{rng['x'][1]},\n y {rng['y'][0]}-{rng['y'][1]})", fill=INK, font=font(11))
                    continue
                n = fr[ref]["n"]
                hw = 9  # native px half-window
                nx0, ny0 = rep["native_xy_0based"]
                ds = rec["display_scale"]
                ny_, nx_ = n["img"].shape
                tile = np.full((2 * hw + 1, 2 * hw + 1, 3), 40, np.uint8)
                for j in range(-hw, hw + 1):
                    for i in range(-hw, hw + 1):
                        xx, yy = nx0 + i, ny0 + j
                        if 0 <= xx < nx_ and 0 <= yy < ny_:
                            v = n["img"][yy, xx]
                            if np.isfinite(v):
                                gg = int(grey_formula([v], ds["low"], ds["high"], ds["asinh_softening"])[0])
                                tile[hw - j, i + hw] = (gg, gg, gg)  # flip: detector +y up
                            else:
                                tile[hw - j, i + hw] = (70, 120, 210)
                sc = T / (2 * hw + 1)
                im.paste(Image.fromarray(tile).resize((T, T), Image.NEAREST), (x0, y0))
                dr.rectangle([x0 + hw * sc, y0 + hw * sc, x0 + (hw + 1) * sc, y0 + (hw + 1) * sc], outline=(0, 200, 230), width=2)
                for s in stars:
                    if ref in "PQ":
                        ddx = s[ref]["detector_xy"][0] - F1_DETECTOR_XY[0]
                        ddy = s[ref]["detector_xy"][1] - F1_DETECTOR_XY[1]
                        if abs(ddx) <= hw and abs(ddy) <= hw:
                            X, Y = x0 + (ddx + hw + 0.5) * sc, y0 + (hw - ddy + 0.5) * sc
                            dr.ellipse([X - 8, Y - 8, X + 8, Y + 8], outline=(40, 170, 60), width=2)
                dr.text((x0 + 4, y0 + T - 16), f"detector x {F1_DETECTOR_XY[0]-hw}-{F1_DETECTOR_XY[0]+hw}, y up", fill=(255, 255, 255), font=font(10))
        y += T + lab + 8
    # F2 row
    if "P" in f2:
        p2 = f2["P"]["display_xy"]
        c2x, c2y = int(round(p2[0])), int(round(p2[1]))
        dr.text((pad, y), f"F2 (P-only feature), sky grid + flag overlay. Magenta + = P feature position (detector {f2['P']['detector_xy_0based_active']})",
                fill=INK, font=font(11, True))
        for col, ref in enumerate("PQR"):
            x0, y0 = pad + col * (T + pad), y + lab
            dr.text((x0, y + 16), f"{ref} {fr[ref]['key']}", fill=MUTED, font=font(10))
            im.paste(tile_sky(ref, c2x, c2y, flags=True), (x0, y0))
            mark(x0, y0, c2x, c2y, *p2, C_MAG)
        y += T + lab + 8
    a = f1["apparent_shift_P_to_Q"]
    u = f1["usable_field_sources_P_Q"]
    dr.text((pad, y), f"F1 P->Q: same detector pixel lands {a['same_detector_pixel_sky_separation_arcsec']}\" apart on the sky "
            f"({a['same_detector_pixel_display_distance_px']} display px); observed footprint shift {a['observed_footprint_centroid_distance_px']} px.",
            fill=INK, font=font(11))
    dr.text((pad, y + 16), f"Usable field stars (n={u['n']}): median sky shift {u['sky_shift_arcsec']['median']}\", max {u['sky_shift_arcsec']['max']}\". "
            "Flag names are pipeline labels; physical cause not established.", fill=INK, font=font(11))
    save_png(im, ctx.out / "B_flagged_features.png", colors=160)


# ============================================================== control C
def pa_of_native_y(n, x, y):
    (ra0, d0), (ra1, d1) = n["cel"].all_pix2world([[x, y], [x, y + 1]], 0)
    de = (ra1 - ra0) * math.cos(math.radians(d0))
    dn = d1 - d0
    return math.degrees(math.atan2(de, dn)) % 360.0


def control_C(ctx):
    rows = []
    sets = [("epsilon_indi_b", "fair_comparison", ctx.eps), ("wise_0855", "transfer exercise (staged, not shipped)", ctx.wise)]
    by = {}
    for preset, case, frs in sets:
        for ref, fr in frs.items():
            rec, n = fr["rec"], fr["n"]
            ih, ph = n["hdr"], n["primary"]
            sp = rec["sampled_position"]
            det = n["det"].wcs_pix2world([[sp["native_x"], sp["native_y"]]], 0)[0]
            sw = WCS(header=proc._without_sip(ih), fobj=fr["hd"], key="W")
            wl2, bw2 = (float(v) for v in sw.pixel_to_world_values(sp["native_x"], sp["native_y"]))
            row = {
                "set": case, "ref": ref, "frame_key": fr["key"], "record_dir": f"{preset}/{fr['subdir']}",
                "observed_at_utc": rec["observed_at_utc"], "mjd": rec["mjd"],
                "header_DATE_AVG": ih["DATE-AVG"], "date_matches_header": rec["observed_at_utc"].rstrip("Z") == ih["DATE-AVG"],
                "obsid": str(ih["OBSID"]).strip(), "detector": rec["detector"], "header_DETECTOR": int(ih["DETECTOR"]),
                "wavelength_um": rec["wavelength_um"], "bandwidth_um": rec["bandwidth_um"],
                "wavelength_recomputed_um": wl2, "wavelength_recomputed_abs_diff": abs(wl2 - rec["wavelength_um"]),
                "collection_id": rec["collection_id"], "pipeline_version": rec["provenance"]["pipeline_version"],
                "ssdc_software_version": rec["provenance"]["ssdc_software_version"],
                "header_VERSION": str(ph.get("VERSION")).strip(), "processing_version": rec["provenance"]["processing_version"],
                "l2_dqa": rec["provenance"]["l2_dqa"], "psf_fwhm_arcsec_header_median": r(ih.get("PSF_FWHM"), 3),
                "exposure_s": r(ih.get("XPOSURE"), 3),
                "target_detector_xy": r(det, 2), "native_y_axis_PA_deg_E_of_N": r(pa_of_native_y(n, sp["native_x"], sp["native_y"]), 3),
                "display_mode": rec["display_scale"]["mode"], "display_low": rec["display_scale"]["low"],
                "display_high": rec["display_scale"]["high"], "quality_status": rec["quality"]["status"],
                "quality_flags": "|".join(rec["quality"]["flag_names"]),
                "adverse_over_screened": f"{rec['quality']['adverse_aperture_pixels']}/{rec['quality']['screened_pixels']}",
                "grid_id": rec["registration"]["grid_id"], "sha_record_manifest_file_equal": fr["sha_all_equal"],
            }
            rows.append(row)
            by[(case, ref)] = row
    pairs = []
    for case, a, b in [("fair_comparison", "A", "B"), ("fair_comparison", "A", "C"), ("fair_comparison", "B", "C"),
                       ("transfer exercise (staged, not shipped)", "P", "Q"), ("transfer exercise (staged, not shipped)", "P", "R"),
                       ("transfer exercise (staged, not shipped)", "Q", "R")]:
        x, y = by[(case, a)], by[(case, b)]
        dl = abs(y["wavelength_um"] - x["wavelength_um"])
        bwmin, bwmean = min(x["bandwidth_um"], y["bandwidth_um"]), (x["bandwidth_um"] + y["bandwidth_um"]) / 2
        lo = max(x["wavelength_um"] - x["bandwidth_um"] / 2, y["wavelength_um"] - y["bandwidth_um"] / 2)
        hi = min(x["wavelength_um"] + x["bandwidth_um"] / 2, y["wavelength_um"] + y["bandwidth_um"] / 2)
        dt = abs(y["mjd"] - x["mjd"])
        differs = []
        if dt != 0: differs.append("time")
        if x["obsid"] != y["obsid"]: differs.append("exposure (OBSID)")
        if dl != 0: differs.append("wavelength")
        if x["bandwidth_um"] != y["bandwidth_um"]: differs.append("bandwidth")
        if x["detector"] != y["detector"]: differs.append("detector")
        if x["collection_id"] != y["collection_id"]: differs.append("release (collection)")
        if x["pipeline_version"] != y["pipeline_version"]: differs.append("pipeline build")
        if x["ssdc_software_version"] != y["ssdc_software_version"]: differs.append("SSDC software version")
        if x["psf_fwhm_arcsec_header_median"] != y["psf_fwhm_arcsec_header_median"]: differs.append("header PSF FWHM")
        if (x["display_low"], x["display_high"]) != (y["display_low"], y["display_high"]): differs.append("display stretch")
        if x["quality_status"] != y["quality_status"] or x["quality_flags"] != y["quality_flags"]: differs.append("quality screen")
        same_det = x["detector"] == y["detector"]
        if same_det and x["target_detector_xy"] != y["target_detector_xy"]: differs.append("pointing (target detector position)")
        rule = x["detector"] == y["detector"] and dl < bwmin
        pairs.append({
            "set": case, "pair": f"{a}-{b}", "frames": f"{x['frame_key']} / {y['frame_key']}",
            "delta_t_days": r(dt, 4), "delta_t_hours": r(dt * 24, 3), "same_exposure": x["obsid"] == y["obsid"],
            "delta_lambda_um": r(dl, 6),
            "dl_over_min_bandwidth": r(dl / bwmin, 4), "dl_over_mean_bandwidth": r(dl / bwmean, 4),
            "dl_over_mean_lambda": r(dl / ((x["wavelength_um"] + y["wavelength_um"]) / 2), 5),
            "tophat_band_overlap_fraction_of_narrower": r(max(0.0, hi - lo) / bwmin, 4),
            "same_detector": x["detector"] == y["detector"],
            # detector coordinates are only comparable on the same detector array
            "target_detector_shift_px": r(math.hypot(y["target_detector_xy"][0] - x["target_detector_xy"][0],
                                                     y["target_detector_xy"][1] - x["target_detector_xy"][1]), 2) if same_det else None,
            "native_y_PA_difference_deg": r(((y["native_y_axis_PA_deg_E_of_N"] - x["native_y_axis_PA_deg_E_of_N"] + 180) % 360) - 180, 3),
            "psf_fwhm_ratio": r(y["psf_fwhm_arcsec_header_median"] / x["psf_fwhm_arcsec_header_median"], 3),
            "processor_shared_stretch_rule_eligible": rule,
            "differs": "; ".join(differs),
        })
    res = {
        "question": "For each pair, which observing, processing and display variables differ, and how closely are "
                    "the target wavelengths matched relative to the channel band widths?",
        "normalization": {
            "primary": "delta_lambda / min(bandwidth_1, bandwidth_2), using each record's bandwidth_um (the WCS-WAVE "
                       "'approximated per-pixel bandwidth' at the target) - the same normalization tools/ingest uses",
            "also_reported": ["delta_lambda / mean(bandwidth)", "delta_lambda / mean(lambda)",
                              "top-hat overlap: overlap of [lambda +- bw/2] intervals divided by the narrower band (an idealization; "
                              "real SPHEREx channel responses are not top-hats)"],
        },
        "processor_rule": "tools/ingest shared_groups_for_case: frames share a display stretch when same detector and "
                          "delta_lambda < min(bandwidth). This is Perigee's display grouping rule, not a scientific "
                          "threshold for when comparisons are valid.",
        "differs_rule": "A variable is listed in 'differs' when its values are not exactly equal. No threshold is applied; "
                        "magnitudes are in the numeric columns.",
        "frames": rows, "pairs": pairs,
    }
    ctx.results["C"] = res
    write_csv(ctx.out / "C_frames.csv", rows)
    write_csv(ctx.out / "C_pairs.csv", pairs)
    figure_C(ctx, pairs)
    return res


def figure_C(ctx, pairs):
    W, H = 1060, 520
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    derived_banner(dr, W, "control C: time apart vs wavelength mismatch per pair")
    px0, py0, pw, ph = 110, 60, 720, 330
    dr.rectangle([px0, py0, px0 + pw, py0 + ph], outline=MUTED)
    xl, xh = -3.5, 2.5  # log10(dl / min bw)
    yl, yh = -1.0, 3.0  # log10(days); same exposure drawn below
    def X(v): return px0 + (math.log10(max(v, 10 ** xl)) - xl) / (xh - xl) * pw
    def Y(d): return py0 + ph - (math.log10(d) - yl) / (yh - yl) * ph
    for e in range(int(xl), int(xh) + 1):
        dr.line([X(10 ** e), py0, X(10 ** e), py0 + ph], fill=(225, 225, 225))
        dr.text((X(10 ** e) - 14, py0 + ph + 4), f"1e{e}", fill=MUTED, font=font(10))
    for e in range(int(yl), int(yh) + 1):
        dr.line([px0, Y(10 ** e), px0 + pw, Y(10 ** e)], fill=(225, 225, 225))
        dr.text((px0 - 50, Y(10 ** e) - 6), f"{10 ** e:g} d", fill=MUTED, font=font(10))
    same_y = py0 + ph + 40
    dr.text((px0 - 100, same_y - 6), "same exposure", fill=MUTED, font=font(10))
    dr.line([px0, same_y, px0 + pw, same_y], fill=(225, 225, 225))
    x1 = X(1.0)
    for yy in range(py0, same_y + 6, 6):
        dr.line([x1, yy, x1, yy + 3], fill=(170, 170, 170))
    dr.text((x1 + 4, py0 + 4), "dl = 1 band width (reference line only,\nnot a validity threshold)", fill=MUTED, font=font(10))
    placed = []
    for p in pairs:
        col = C_P if p["set"] == "fair_comparison" else C_Q
        x = X(p["dl_over_min_bandwidth"])
        y = same_y if p["delta_t_days"] == 0 else Y(p["delta_t_days"])
        dr.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col)
        name = ("Eps " if p["set"] == "fair_comparison" else "WISE ") + p["pair"]
        txt = f"{name}  ({p['delta_t_days']:g} d, {p['dl_over_min_bandwidth']:g} bw)"
        tw = dr.textlength(txt, font=font(11))
        tx = x + 9 if x + 9 + tw < W - 6 else x - 9 - tw
        ty = y - 7
        while any(abs(ty - py) < 14 and abs(tx - px) < 200 for px, py in placed):
            ty += 15
        placed.append((tx, ty))
        if ty != y - 7:
            dr.line([x, y, tx + (0 if tx > x else tw), ty + 7], fill=(180, 180, 180))
        dr.text((tx, ty), txt, fill=INK, font=font(11))
    dr.text((px0 + pw / 2 - 160, py0 + ph + 60), "delta lambda / min band width at the target (log scale)", fill=INK, font=font(11))
    dr.text((10, H - 40), "Each point is a pair. Wavelength and time are only two of the variables; the 'differs' column of "
            "C_pairs.csv also lists detector, release,", fill=MUTED, font=font(10))
    dr.text((10, H - 24), "pipeline build, PSF, stretch, quality and pointing differences. Blue = Epsilon Indi B case, orange = WISE 0855 staged exercise.",
            fill=MUTED, font=font(10))
    save_png(im, ctx.out / "C_time_vs_wavelength.png")


# ============================================================== control D
def glow_centre_native(img, x, y, r_=4.0, iters=6):
    ny, nx = img.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    cx, cy = x, y
    for _ in range(iters):
        d = np.hypot(xx - cx, yy - cy)
        win = d <= r_
        ann = (d > r_ + 2) & (d <= r_ + 6) & np.isfinite(img)
        bg = np.median(img[ann])
        v = img.copy()
        top = np.nanmax(np.where(win, img, np.nan))
        v[win & ~np.isfinite(img)] = top
        w = np.clip(np.where(win, v, 0) - bg, 0, None)
        cx, cy = float((w * xx).sum() / w.sum()), float((w * yy).sum() / w.sum())
    return cx, cy


def glow_centre_png(gray, alpha, x, y, half=7, iters=6):
    g = gray.astype(float)
    cx, cy = x, y
    for _ in range(iters):
        ix, iy = int(math.floor(cx)), int(math.floor(cy))
        win = g[iy - half: iy + half + 1, ix - half: ix + half + 1].copy()
        a = alpha[iy - half: iy + half + 1, ix - half: ix + half + 1]
        win[a == 0] = 255.0
        big = g[iy - 20: iy + 21, ix - 20: ix + 21]
        bg = np.median(big[alpha[iy - 20: iy + 21, ix - 20: ix + 21] > 0])
        w = np.clip(win - bg, 0, None)
        yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
        cx = float((w * (xx + 0.5)).sum() / w.sum())
        cy = float((w * (yy + 0.5)).sum() / w.sum())
    return cx, cy


def nonfinite_core_centroid(n, x, y, rad=3.0):
    img = n["img"]
    ny, nx = img.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    m = (np.hypot(xx - x, yy - y) <= rad) & ~np.isfinite(img)
    if not m.any():
        return None, 0
    return (float(xx[m].mean()), float(yy[m].mean())), int(m.sum())


def png_star_centroid(gray, alpha, x, y, half=4):
    size = gray.shape[0]
    ix, iy = int(math.floor(x)), int(math.floor(y))
    if ix - 12 < 0 or iy - 12 < 0 or ix + 13 > size or iy + 13 > size:
        return None
    if (alpha[iy - 12: iy + 13, ix - 12: ix + 13] == 0).any():
        return None
    bg = np.median(gray[iy - 12: iy + 13, ix - 12: ix + 13].astype(float))
    w = np.clip(gray[iy - half: iy + half + 1, ix - half: ix + half + 1].astype(float) - bg, 0, None)
    if w.sum() <= 0:
        return None
    yy, xx = np.mgrid[iy - half: iy + half + 1, ix - half: ix + half + 1]
    return float((w * (xx + 0.5)).sum() / w.sum()), float((w * (yy + 0.5)).sum() / w.sum())


def vec(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return {"dx": r(dx, 2), "dy": r(dy, 2), "dist_px": r(math.hypot(dx, dy), 2),
            "dist_arcsec": r(math.hypot(dx, dy) * 1.40625, 2),
            "direction_deg_E_of_N": r(math.degrees(math.atan2(-dx, -dy)), 1)}  # signed (-180, 180], east positive


def control_D(ctx):
    preset = "barnards_star"
    gw, size = grid_for(ctx, preset)
    case, pf = ctx.barn, ctx.barn_pf
    gaia = gaia_rows(ctx, "barnards_star")
    markers = {ref: (case[ref]["rec"]["marker"]["x"], case[ref]["rec"]["marker"]["y"]) for ref in "ABC"}
    proxies = {}

    def add(name, family, window, ref, xy):
        proxies.setdefault(name, {"family": family, "window": window, "xy": {}})["xy"][ref] = None if xy is None else r(xy, 3)

    for ref in "ABC":
        m = markers[ref]
        for half in (5, 7, 10, 15):
            add(f"png_shared_half{half}", "glow centre on the case PNG (shared stretch); transparent core counted white",
                f"{2 * half + 1}x{2 * half + 1} display px", ref, glow_centre_png(case[ref]["gray"], case[ref]["alpha"], *m, half=half))
        for half in (7, 15):
            add(f"png_perframe_half{half}", "glow centre on the shipped per-frame-stretch preset PNG; transparent core counted white",
                f"{2 * half + 1}x{2 * half + 1} display px", ref, glow_centre_png(pf[ref]["gray"], pf[ref]["alpha"], *m, half=half))
        n = case[ref]["n"]
        sp = case[ref]["rec"]["sampled_position"]
        for rad in (3, 4, 5, 6):
            cx, cy = glow_centre_native(n["img"], sp["native_x"], sp["native_y"], r_=rad)
            ra, dec = n["cel"].all_pix2world([[cx, cy]], 0)[0]
            add(f"native_r{rad}", "glow centre on native pixels (non-finite core = window max), mapped through the header WCS",
                f"r = {rad} native px", ref, sky_to_display_px(gw, size, ra, dec))
        c, _ = nonfinite_core_centroid(n, sp["native_x"], sp["native_y"])
        if c is not None:
            ra, dec = n["cel"].all_pix2world([[c[0], c[1]]], 0)[0]
            c = sky_to_display_px(gw, size, ra, dec)
        add("nonfinite_core", "centroid of non-finite (saturated, no value) native pixels within 3 native px", "r = 3 native px", ref, c)

    shifts = {}
    for name, p in proxies.items():
        xy = p["xy"]
        s = {}
        for a, b in (("A", "B"), ("A", "C")):
            s[f"{a}{b}"] = vec(xy[a], xy[b]) if xy[a] is not None and xy[b] is not None else None
        shifts[name] = s
    marker_shift = {f"{a}{b}": vec(markers[a], markers[b]) for a, b in (("A", "B"), ("A", "C"))}

    # field stars on the case PNGs
    common = None
    per = {}
    for ref in "ABC":
        n = case[ref]["n"]
        ok = set()
        for g in gaia:
            if g["source_id"] == BARNARD_GAIA_ID:
                continue
            ra, dec = gaia_at(g, case[ref]["rec"]["mjd"])
            ex, ey = n["cel"].all_world2pix([[ra, dec]], 0)[0]
            c = native_star_centroid(n, ex, ey, flag_free=False)
            if c is not None and math.hypot(c[0] - ex, c[1] - ey) <= 1.0:
                ok.add(g["source_id"])
                per[(ref, g["source_id"])] = sky_to_display_px(gw, size, ra, dec)
        common = ok if common is None else common & ok
    ref_stars = []
    for g in sorted(gaia, key=lambda g: g["phot_g_mean_mag"]):
        if g["source_id"] not in (common or set()):
            continue
        row = {"gaia_dr3": g["source_id"], "G": r(g["phot_g_mean_mag"], 2)}
        for ref in "ABC":
            row[ref] = png_star_centroid(case[ref]["gray"], case[ref]["alpha"], *per[(ref, g["source_id"])])
        if all(row[k] for k in "ABC") and all(math.hypot(row["A"][0] - k["A"][0], row["A"][1] - k["A"][1]) > 5 for k in ref_stars):
            row["AB"] = vec(row["A"], row["B"])
            row["AC"] = vec(row["A"], row["C"])
            for k in "ABC":
                row[k] = r(row[k], 3)
            ref_stars.append(row)
    fs_max = max([max(abs(s["AB"]["dx"]), abs(s["AB"]["dy"]), abs(s["AC"]["dx"]), abs(s["AC"]["dy"])) for s in ref_stars], default=None)
    fs_maxdist = max([max(s["AB"]["dist_px"], s["AC"]["dist_px"]) for s in ref_stars], default=None)

    ac = [s["AC"] for s in shifts.values() if s["AC"]]
    ab = [s["AB"] for s in shifts.values() if s["AB"]]
    summary = {
        "n_proxies": len(proxies),
        "AC_dist_px_range": [min(v["dist_px"] for v in ac), max(v["dist_px"] for v in ac)],
        "AB_dist_px_range": [min(v["dist_px"] for v in ab), max(v["dist_px"] for v in ab)],
        "AC_direction_deg_range": [min(v["direction_deg_E_of_N"] for v in ac), max(v["direction_deg_E_of_N"] for v in ac)],
        "AC_proxies_with_dy_negative_north": sum(1 for v in ac if v["dy"] < 0),
        "AB_proxies_with_dy_negative_north": sum(1 for v in ab if v["dy"] < 0),
        "AC_proxy_minus_marker_dist_px_range": [r(min(math.hypot(v["dx"] - marker_shift["AC"]["dx"], v["dy"] - marker_shift["AC"]["dy"]) for v in ac), 2),
                                                 r(max(math.hypot(v["dx"] - marker_shift["AC"]["dx"], v["dy"] - marker_shift["AC"]["dy"]) for v in ac), 2)],
        "field_star_n": len(ref_stars),
        "field_star_max_abs_component_shift_px": fs_max,
        "field_star_max_shift_px": fs_maxdist,
        "AC_min_proxy_over_field_star_max": r(min(v["dist_px"] for v in ac) / fs_maxdist, 2) if fs_maxdist else None,
    }
    warn = {}
    for ref in "ABC":
        q = case[ref]["rec"]["quality"]
        m = markers[ref]
        a = case[ref]["alpha"]
        yy, xx = np.nonzero(a == 0)
        warn[ref] = {"frame_key": case[ref]["key"], "quality_status": q["status"], "flag_names": q["flag_names"],
                     "adverse_over_screened": f"{q['adverse_aperture_pixels']}/{q['screened_pixels']}",
                     "nonfinite_aperture_pixels": q["nonfinite_aperture_pixels"],
                     "transparent_display_px_within_10px_of_marker": int(sum(1 for y_, x_ in zip(yy, xx) if math.hypot(x_ + .5 - m[0], y_ + .5 - m[1]) <= 10))}

    # all retained Barnard frames: one fixed proxy minus marker (descriptive scatter, not selected)
    allf = []
    for f in sorted((PRESETS / preset / "frames").glob("*_D?.json")):
        rec = ctx.inp.json(f)
        if not rec["quality"]["covered"] or rec["marker"] is None:
            continue
        ent = manifest_entry(ctx.manifest, preset, rec["frame_key"])
        hd = fits.open(io.BytesIO(ctx.inp.read(ctx.data_root / ent["file"])), memmap=False)
        n = native(hd)
        sp = rec["sampled_position"]
        try:
            cx, cy = glow_centre_native(n["img"], sp["native_x"], sp["native_y"], r_=4)
        except Exception:
            continue
        ra, dec = n["cel"].all_pix2world([[cx, cy]], 0)[0]
        gx, gy = sky_to_display_px(gw, size, ra, dec)
        allf.append({"frame_key": rec["frame_key"], "detector": rec["detector"], "wavelength_um": r(rec["wavelength_um"], 4),
                     "dx": r(gx - rec["marker"]["x"], 2), "dy": r(gy - rec["marker"]["y"], 2),
                     "dist": r(math.hypot(gx - rec["marker"]["x"], gy - rec["marker"]["y"]), 2)})
        hd.close()
    d_all = [a["dist"] for a in allf]
    res = {
        "question": "In the Barnard case, do image-based visual proxies show the glow moving relative to the field stars "
                    "in the direction and roughly the size of the catalog prediction, and how much do they depend on the method/window?",
        "frames": {ref: case[ref]["key"] for ref in "ABC"},
        "warning_saturated_core": warn,
        "catalog_prediction": {"marker_xy": {k: r(v, 3) for k, v in markers.items()}, "shift": marker_shift,
                               "basis": "processor A marker: catalog position propagated with proper motion (annual parallax not modeled). "
                                        "Not measured from the images."},
        "image_proxies": {k: {"family": v["family"], "window": v["window"], "xy": v["xy"], "shift": shifts[k]} for k, v in proxies.items()},
        "field_stars_case_png": ref_stars,
        "summary": summary,
        "all_retained_frames_native_r4_minus_marker": {
            "n": len(allf), "median_dx": r(np.median([a["dx"] for a in allf]), 2), "median_dy": r(np.median([a["dy"] for a in allf]), 2),
            "dist_min": min(d_all), "dist_median": r(np.median(d_all), 2), "dist_max": max(d_all),
            "note": "Every retained Barnard frame whose record covers the star (mixed detectors/wavelengths). Descriptive "
                    "spread of one proxy around the prediction; not a sampling-based uncertainty.",
            "frames": allf},
    }
    ctx.results["D"] = res
    rows = []
    for k, v in res["image_proxies"].items():
        for pr in ("AB", "AC"):
            s = v["shift"][pr]
            rows.append({"proxy": k, "family": v["family"], "window": v["window"], "pair": pr,
                         **({kk: s[kk] for kk in ("dx", "dy", "dist_px", "dist_arcsec", "direction_deg_E_of_N")} if s else {})})
    for pr in ("AB", "AC"):
        s = marker_shift[pr]
        rows.append({"proxy": "catalog_prediction_marker", "family": "catalog prediction (not an image measurement)", "window": "",
                     "pair": pr, **{kk: s[kk] for kk in ("dx", "dy", "dist_px", "dist_arcsec", "direction_deg_E_of_N")}})
    write_csv(ctx.out / "D_barnard_proxies.csv", rows)
    figure_D(ctx, res)
    return res


def figure_D(ctx, res):
    case = ctx.barn
    half, z = 32, 4
    T = 2 * half * z
    pad = 12
    W = pad + 3 * (T + pad)
    H = 26 + 40 + T + 30 + 12 * 26 + 60 + 60
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    derived_banner(dr, W, "control D: Barnard's Star glow vs catalog prediction vs field stars")
    mA = res["catalog_prediction"]["marker_xy"]["A"]
    cx, cy = int(round(mA[0])), int(round(mA[1])) - 4
    y0 = 26 + 40
    pal = {"png_shared": (230, 160, 0), "png_perframe": (0, 170, 200), "native": (60, 170, 60), "nonfinite": (200, 60, 60)}
    def pcol(name):
        return next(c for k, c in pal.items() if name.startswith(k))
    for col, ref in enumerate("ABC"):
        x0 = pad + col * (T + pad)
        rec = case[ref]["rec"]
        dr.text((x0, 30), f"{ref} {case[ref]['key']}  {rec['observed_at_utc'][:10]}", fill=INK, font=font(11, True))
        dr.text((x0, 46), "case PNG, shared stretch, 4x; blue = no value", fill=MUTED, font=font(10))
        rgb = grey_rgb(case[ref]["gray"], case[ref]["alpha"])
        crop = rgb[cy - half: cy + half, cx - half: cx + half]
        im.paste(Image.fromarray(crop).resize((T, T), Image.NEAREST), (x0, y0))
        def Pt(x, y): return x0 + (x - (cx - half)) * z, y0 + (y - (cy - half)) * z
        _, gy = Pt(0, mA[1])
        dr.line([x0, gy, x0 + T, gy], fill=(0, 220, 120), width=1)
        mx, my = Pt(*res["catalog_prediction"]["marker_xy"][ref])
        for a, b in (((-14, 0), (-6, 0)), ((6, 0), (14, 0)), ((0, -14), (0, -6)), ((0, 6), (0, 14))):
            dr.line([mx + a[0], my + a[1], mx + b[0], my + b[1]], fill=C_MAG, width=2)
        for name, p in res["image_proxies"].items():
            xy = p["xy"][ref]
            if xy:
                X, Y = Pt(*xy)
                dr.ellipse([X - 3, Y - 3, X + 3, Y + 3], fill=pcol(name))
    # shift plane
    py0 = y0 + T + 30
    dr.text((pad, py0 - 4), "Shift of each visual proxy, A->B (hollow) and A->C (filled), in display px; north up. "
            "Magenta = catalog prediction; grey = field stars.", fill=INK, font=font(11, True))
    sc = 26
    cxp, cyp = W // 2 - 160, py0 + 30 + 10 * sc
    for gx in range(-5, 6):
        dr.line([cxp + gx * sc, cyp - 10 * sc, cxp + gx * sc, cyp + 2 * sc], fill=(232, 232, 232))
        dr.text((cxp + gx * sc - 4, cyp + 2 * sc + 3), f"{gx}", fill=MUTED, font=font(9))
    for gy_ in range(-10, 3):
        dr.line([cxp - 5 * sc, cyp + gy_ * sc, cxp + 5 * sc, cyp + gy_ * sc], fill=(232, 232, 232))
        if gy_ % 2 == 0:
            dr.text((cxp - 5 * sc - 20, cyp + gy_ * sc - 6), f"{gy_}", fill=MUTED, font=font(9))
    dr.line([cxp - 5 * sc, cyp, cxp + 5 * sc, cyp], fill=MUTED)
    dr.line([cxp, cyp - 10 * sc, cxp, cyp + 2 * sc], fill=MUTED)
    dr.text((cxp + 4, cyp - 10 * sc + 2), "north (dy < 0)", fill=MUTED, font=font(10))
    dr.text((cxp + 5 * sc - 44, cyp + 4), "+dx (west)", fill=MUTED, font=font(10))
    for s in res["field_stars_case_png"]:
        for pr in ("AB", "AC"):
            X, Y = cxp + s[pr]["dx"] * sc, cyp + s[pr]["dy"] * sc
            dr.ellipse([X - 3, Y - 3, X + 3, Y + 3], outline=(140, 140, 140))
    for name, p in res["image_proxies"].items():
        for pr, fill in (("AB", False), ("AC", True)):
            s = p["shift"][pr]
            if s:
                X, Y = cxp + s["dx"] * sc, cyp + s["dy"] * sc
                if fill:
                    dr.ellipse([X - 4, Y - 4, X + 4, Y + 4], fill=pcol(name))
                else:
                    dr.ellipse([X - 4, Y - 4, X + 4, Y + 4], outline=pcol(name), width=2)
    for pr in ("AB", "AC"):
        s = res["catalog_prediction"]["shift"][pr]
        X, Y = cxp + s["dx"] * sc, cyp + s["dy"] * sc
        dr.line([X - 12, Y, X + 12, Y], fill=C_MAG, width=3); dr.line([X, Y - 12, X, Y + 12], fill=C_MAG, width=3)
    lx = cxp + 5 * sc + 40
    for i, (k, lab) in enumerate((("png_shared", "case PNG glow, windows 11/15/21/31 px"), ("png_perframe", "per-frame PNG glow, 15/31 px"),
                                  ("native", "native glow, r = 3/4/5/6 native px"), ("nonfinite", "non-finite core centroid"))):
        dr.ellipse([lx, py0 + 60 + i * 20, lx + 8, py0 + 68 + i * 20], fill=pal[k])
        dr.text((lx + 14, py0 + 57 + i * 20), lab, fill=INK, font=font(11))
    sm = res["summary"]
    dr.text((lx, py0 + 160), f"A->C proxy distance: {sm['AC_dist_px_range'][0]}-{sm['AC_dist_px_range'][1]} px\n"
            f"catalog prediction: {res['catalog_prediction']['shift']['AC']['dist_px']} px\n"
            f"proxies pointing north: {sm['AC_proxies_with_dy_negative_north']}/{sm['n_proxies']}\n"
            f"field stars (n={sm['field_star_n']}): max shift {sm['field_star_max_shift_px']} px", fill=INK, font=font(11))
    dr.text((pad, H - 40), "Visual proxies of a saturated, flagged glow - not centroids, not astrometry, not a proper-motion measurement. "
            "1 display px = 1.406\".", fill=MUTED, font=font(11))
    dr.text((pad, H - 22), "Green line fixed at A's marker y. Every frame is quality-flagged at the star (BLOOM/OVERFLOW/...).",
            fill=MUTED, font=font(11))
    save_png(im, ctx.out / "D_barnard_proxies.png")


# ============================================================== control E
FIELDS = ["pixels", "time", "wavelength", "scale", "quality", "provenance"]
FIELD_DESC = {
    "pixels": "the PNG pixel arrays only (already on a common grid, but neither grid nor order is stated)",
    "time": "mid-exposure date/time of each frame",
    "wavelength": "wavelength and band width at the target",
    "scale": "display stretch parameters (mode, low, high, unit) plus grid scale/orientation/registration",
    "quality": "quality screen status, flag overlay and flag meanings",
    "provenance": "frame keys, detector, release, pipeline build, hashes, source URLs, raw-FITS access "
                  "(native values, detector coordinates) and the marker labelled as a catalog prediction",
}


def control_E(ctx):
    A, B, C, D = (ctx.results[k] for k in "ABCD")
    pq = next(p for p in C["pairs"] if p["pair"] == "P-Q")
    pr_ = next(p for p in C["pairs"] if p["pair"] == "P-R")
    ac = next(p for p in C["pairs"] if p["pair"] == "A-C")
    f1 = B["F1_PQ_detector_pixel"]
    p1 = next(p for p in A["probes"] if p["value_MJy_sr"] == 1.0)
    reps = {}
    reps["I0 images only"] = {"pixels"}
    acc = {"pixels"}
    for f in FIELDS[1:]:
        acc = acc | {f}
        reps[f"I{len(reps)} +{f}"] = set(acc)
    for f in FIELDS[1:]:
        reps[f"full minus {f}"] = set(FIELDS) - {f}

    # empirical evidence about what the bare PNGs carry
    text_chunks = {}
    for grp, frs in (("wise", ctx.wise), ("eps", ctx.eps), ("barn", ctx.barn)):
        for ref, fr in frs.items():
            text_chunks[f"{grp}:{ref}"] = png_has_text_chunks(fr["png_bytes"])
    # grey of F1 vs brightest star block in P PNG
    gP = ctx.wise["P"]["gray"]
    fpx = f1["per_frame"]["P"]["display_xy"]
    fwin = gP[int(fpx[1]) - 3:int(fpx[1]) + 4, int(fpx[0]) - 3:int(fpx[0]) + 4]
    star_blocks = []
    for s in f1["usable_field_sources_P_Q"]["stars"]:
        sx, sy = s["P"]["display_xy_from_native"]
        w = gP[int(sy) - 3:int(sy) + 4, int(sx) - 3:int(sx) + 4]
        star_blocks.append({"gaia_dr3": s["gaia_dr3"], "max_grey": int(w.max()), "white_px_7x7": int((w == 255).sum())})
    evidence_images_only = {
        "png_metadata_chunks_present": text_chunks,
        "png_metadata_note": "Processor A PNGs carry no tEXt/zTXt/iTXt/eXIf/tIME chunks, so the image files alone contain no date, wavelength, stretch or provenance.",
        "F1_in_P_png": {"max_grey": int(fwin.max()), "white_px_7x7": int((fwin == 255).sum())},
        "usable_field_star_blocks_in_P_png": star_blocks,
        "note": f"In the P PNG the flagged feature reaches grey {int(fwin.max())} ({int((fwin == 255).sum())} white px in 7x7); "
                f"{sum(1 for b in star_blocks if b['max_grey'] == 255)} of {len(star_blocks)} usable field-star cores also reach 255. "
                "Nearest-neighbour upsampling turns every native pixel into a ~4.4 display-px block. A compact block hints at a "
                "single native pixel, but the pipeline's flag judgement is not in the pixels.",
    }

    Qs = [
        dict(id="Q1", case="WISE P/Q/R", q="Which pair is closer in time, and by how much?", need={"time"},
             yes=f"P/Q {pq['delta_t_days']} d apart; P/R {pr_['delta_t_days']} d (control C).",
             cannot="Without times, image order and spacing are unknown."),
        dict(id="Q2", case="WISE P/Q/R", q="Which pair has closely matched target wavelength for a temporal comparison?",
             need={"time", "wavelength"},
             yes=f"P/Q: delta-lambda {pq['dl_over_min_bandwidth']} of a band width; P/R: {pr_['dl_over_min_bandwidth']} band widths (control C). "
                 f"P/Q still differ in: {pq['differs']}.", cannot="Wavelength is not visible in the pixels."),
        dict(id="Q3", case="WISE P/Q", q="Does the same physical value get the same grey level in P and Q as shipped?",
             need={"scale"},
             yes=f"No: 1.0 MJy/sr is grey {p1['grey_P_per_frame']} in P and {p1['grey_Q_per_frame']} in Q (per-frame); "
                 f"{p1['grey_P_shared']} in both under the shared stretch (control A).",
             cannot="Grey levels cannot be converted to physical values without the stretch."),
        dict(id="Q4", case="WISE P/Q", q="Can 'Q looks brighter' be split into display mapping vs physical values?",
             need={"scale", "provenance"}, partial={"scale"},
             yes=f"Yes: as shipped, Q's median grey is higher ({A['mapping_checks']['Q_per_frame']['median_grey']:g} vs "
                 f"{A['mapping_checks']['P_per_frame']['median_grey']:g}) although Q's physical grid median is "
                 f"{A['physical_median_ratio_Q_over_P']} x P's; under the shared stretch Q's median grey is lower "
                 f"({A['mapping_checks']['Q_shared']['median_grey']:g} vs {A['mapping_checks']['P_shared']['median_grey']:g}). "
                 "'Q is brighter' is not supported by the physical values; the cause of the small physical difference is not established.",
             part="The stretch shows the mapping differs, but not whether the physical values also differ.",
             cannot="No representation here establishes the cause of a physical background difference."),
        dict(id="Q5", case="WISE P/Q", q="Is the 'jumping' dot covered by an adverse pipeline flag?", need={"quality"},
             yes=f"Yes: {', '.join(f1['per_frame']['P']['flag_names_adverse'])} in P and Q (control B).",
             cannot="The pixels show a compact white block, the same grey as star cores; flags are not in the pixels."),
        dict(id="Q6", case="WISE P/Q", q="Is the dot fixed on the detector rather than on the sky?", need={"provenance"},
             yes=f"Yes: same detector pixel {list(F1_DETECTOR_XY)} in P and Q; on the sky it lands "
                 f"{f1['apparent_shift_P_to_Q']['same_detector_pixel_sky_separation_arcsec']}\" apart while usable stars agree to "
                 f"median {f1['usable_field_sources_P_Q']['sky_shift_arcsec']['median']}\" (control B).",
             cannot="Detector coordinates require the raw FITS (key-A WCS)."),
        dict(id="Q7", case="WISE P/Q", q="What physically produced the flagged pixel?", need=None,
             cannot="Not answerable from any representation here. Flag names (e.g. TRANSIENT, NONFUNC) are pipeline labels, not an established cause."),
        dict(id="Q8", case="WISE", q="Is the dot near the marker WISE 0855?", need=None, partial={"provenance"},
             part="Provenance labels the marker as a catalog prediction, not a detection; positional association with a "
                  "catalogued star needs an external catalog (transfer-exercise review).",
             cannot="Identity is not established by any representation here."),
        dict(id="Q9", case="Epsilon A/C", q="Is the A vs C difference a change over time?", need={"time", "wavelength"},
             yes=f"No: same exposure (delta-t {ac['delta_t_days']} d), delta-lambda {ac['dl_over_min_bandwidth']} band widths, "
                 f"detectors differ (control C).", cannot="Images alone look like 'before/after'."),
        dict(id="Q10", case="Epsilon A/C", q="Can grey levels be compared between A and C?", need={"scale"},
             yes="No: both use per-frame stretches with different limits (control C display columns).",
             cannot="Without stretch parameters a viewer cannot tell."),
        dict(id="Q11", case="Barnard A/B/C", q="Does the glow move vs field stars; which direction, which time order?",
             need={"pixels", "scale", "time"}, partial={"pixels"},
             yes=f"Yes, qualitatively: A->C proxies shift {D['summary']['AC_dist_px_range'][0]}-{D['summary']['AC_dist_px_range'][1]} display px, "
                 f"{D['summary']['AC_proxies_with_dy_negative_north']}/{D['summary']['n_proxies']} toward north; field stars move at most "
                 f"{D['summary']['field_star_max_shift_px']} px (control D).",
             part="A positional difference is visible, but co-registration, orientation (north) and time order are not stated.",
             cannot=""),
        dict(id="Q12", case="Barnard A/B/C", q="Is the dark/blue core a dark feature of the star?", need={"quality"},
             yes="No: those pixels are non-finite (saturated, no value) and flagged (control D warning block).",
             cannot="Transparent pixels look like a hole."),
        dict(id="Q13", case="Barnard A/B/C", q="Does the visible shift agree with the catalog-predicted direction?",
             need={"pixels", "time", "scale", "provenance"},
             yes=f"Consistent in direction: prediction A->C {D['catalog_prediction']['shift']['AC']['dist_px']} px at "
                 f"{D['catalog_prediction']['shift']['AC']['direction_deg_E_of_N']:+g} deg from north (east positive); proxy directions "
                 f"{D['summary']['AC_direction_deg_range'][0]:+g} to {D['summary']['AC_direction_deg_range'][1]:+g} deg (control D).",
             cannot="The marker and its basis are needed."),
        dict(id="Q14", case="Barnard A/B/C", q="What is Barnard's Star's proper motion from these images?", need=None,
             cannot=f"Not answerable: saturated, flagged core; proxies span {D['summary']['AC_dist_px_range'][0]}-"
                    f"{D['summary']['AC_dist_px_range'][1]} px depending on method (control D)."),
        dict(id="Q15", case="all", q="Can a reviewer re-obtain and verify the exact source data?", need={"provenance"},
             yes=f"Yes: record sha256 = manifest sha256 = file sha256 for {ctx.integrity['n_all_equal']}/{ctx.integrity['n']} "
                 "frames loaded with records (results.json integrity block); source URLs and pipeline builds in control C.",
             cannot="No source identity in the pixels."),
        dict(id="Q16", case="all", q="Is any brightness change photometrically measured?", need=None,
             cannot="No: nothing here is photometry; stretches are display mappings."),
    ]
    matrix = []
    for qd in Qs:
        row = {"id": qd["id"], "case": qd["case"], "question": qd["q"],
               "required_fields": "|".join(sorted(qd["need"])) if qd["need"] else "not available in any representation"}
        for name, have in reps.items():
            if qd["need"] is not None and qd["need"] <= have:
                row[name] = "yes"
            elif qd.get("partial") and qd["partial"] <= have:
                row[name] = "partial"
            else:
                row[name] = "no"
        row["answer_when_yes"] = qd.get("yes", "")
        row["partial_means"] = qd.get("part", "")
        row["what_is_missing_otherwise"] = qd["cannot"]
        matrix.append(row)
    res = {
        "question": "Which investigation questions can and cannot be answered from the images alone, and from the images "
                    "with time, wavelength, scale, quality and provenance restored?",
        "status": "Information-availability matrix derived from computed facts. Not a human or AI trial; no score.",
        "fields": FIELD_DESC,
        "representations": {k: sorted(v) for k, v in reps.items()},
        "rule": "A cell is 'yes' when every required field is present, 'partial' when the listed partial subset is present, "
                "else 'no'. Required fields were assigned per question from what the computing step in controls A-D needed.",
        "matrix": matrix,
        "evidence_images_only": evidence_images_only,
    }
    ctx.results["E"] = res
    write_csv(ctx.out / "E_information_matrix.csv", matrix)
    figure_E(ctx, res)
    return res


def figure_E(ctx, res):
    tiles = [("WISE P", ctx.wise["P"]), ("WISE Q", ctx.wise["Q"]), ("WISE R", ctx.wise["R"]),
             ("Eps A", ctx.eps["A"]), ("Eps C", ctx.eps["C"]), ("Barnard A", ctx.barn["A"]), ("Barnard C", ctx.barn["C"])]
    T, pad = 176, 10
    W = pad + len(tiles) * (T + pad)
    mtx = res["matrix"]
    reps = list(res["representations"].keys())
    cell_w, qcol = 64, 440
    mat_w = qcol + len(reps) * cell_w + 20
    W = max(W, mat_w)
    meta_h = 112
    H = 26 + 30 + T + 30 + T + meta_h + 40 + 40 + len(mtx) * 20 + 40
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    derived_banner(dr, W, "control E: same images, with and without restored information")
    y0 = 26 + 26
    dr.text((pad, y0 - 22), "Images alone (what the pixels carry: no date, wavelength, stretch, flags or source)", fill=INK, font=font(12, True))
    for i, (lab, fr) in enumerate(tiles):
        x0 = pad + i * (T + pad)
        im.paste(Image.fromarray(grey_rgb(fr["gray"], fr["alpha"], hole=(0, 0, 0))).resize((T, T), Image.BOX), (x0, y0))
        dr.text((x0 + 4, y0 + 4), f"image {i + 1}", fill=(255, 220, 0), font=font(11, True))
    y1 = y0 + T + 30
    dr.text((pad, y1 - 22), "Same images with time, wavelength, scale, quality (red/yellow overlay) and provenance restored",
            fill=INK, font=font(12, True))
    for i, (lab, fr) in enumerate(tiles):
        x0 = pad + i * (T + pad)
        rec = fr["rec"]
        rgb = overlay(grey_rgb(fr["gray"], fr["alpha"]), fr["flags_rgba"])
        tile = Image.fromarray(rgb).resize((T, T), Image.BOX)
        im.paste(tile, (x0, y1))
        if rec.get("marker"):
            mx, my = rec["marker"]["x"] * T / 256, rec["marker"]["y"] * T / 256
            dr.ellipse([x0 + mx - 7, y1 + my - 7, x0 + mx + 7, y1 + my + 7], outline=C_MAG, width=2)
        ds, q = rec["display_scale"], rec["quality"]
        lines = [f"{lab}: {rec['frame_key']}", f"{rec['observed_at_utc'][:16].replace('T', ' ')} UTC",
                 f"lambda {rec['wavelength_um']:.4f} um, bw {rec['bandwidth_um']:.4f}",
                 f"D{rec['detector']} {rec['collection_id']} {rec['provenance']['pipeline_version']}",
                 f"{ds['mode']} {ds['low']:.3f}-{ds['high']:.3f} MJy/sr",
                 f"screen {q['status']}" + ((f": {','.join(q['flag_names'])}" if len(','.join(q['flag_names'])) <= 18
                                            else f" ({len(q['flag_names'])} flag types)") if q["flag_names"] else ""),
                 f"sha256 {rec['provenance']['sha256'][:12]}..."]
        for j, ln in enumerate(lines):
            dr.text((x0, y1 + T + 4 + j * 15), ln, fill=INK if j == 0 else MUTED, font=font(9 if j else 10, j == 0))
    ym = y1 + T + meta_h + 30
    dr.text((pad, ym), "Question x representation (yes / partial / no). Cumulative columns I0-I5, then leave-one-out. "
            "Information availability only - not a trial, not a score.", fill=INK, font=font(12, True))
    ym += 22
    abbrev = {"images only": "pixels", "wavelength": "wave", "quality": "qual", "provenance": "prov", "full minus ": "all -"}
    for j, k in enumerate(reps):
        lab = k
        for a_, b_ in abbrev.items():
            lab = lab.replace(a_, b_)
        dr.text((pad + qcol + j * cell_w + 2, ym), lab, fill=MUTED, font=font(9))
    ym += 18
    colr = {"yes": (60, 160, 90), "partial": (230, 170, 40), "no": (215, 215, 215)}
    for i, row in enumerate(mtx):
        yy = ym + i * 20
        dr.text((pad, yy + 3), f"{row['id']} {row['question']}"[:80], fill=INK, font=font(10))
        for j, k in enumerate(reps):
            x = pad + qcol + j * cell_w
            dr.rectangle([x, yy, x + cell_w - 4, yy + 16], fill=colr[row[k]])
            dr.text((x + 4, yy + 2), row[k], fill=(255, 255, 255) if row[k] != "no" else MUTED, font=font(9))
    dr.text((pad, H - 22), "Magenta circle = catalog prediction (not a detection). Full question text, required fields and answers: E_information_matrix.csv.",
            fill=MUTED, font=font(10))
    save_png(im, ctx.out / "E_information_removal.png", colors=128)


# ============================================================== output utils
def write_csv(path: Path, rows):
    if not rows:
        path.write_text("")
        return
    keys = []
    for rw in rows:
        for k in rw:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        for rw in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in rw.items()})


class Ctx:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-root", required=True, type=Path, help="research/build_data (manifest.json + raw/)")
    ap.add_argument("--out", required=True, type=Path, help="output directory; must be absent or empty")
    a = ap.parse_args()
    t0 = time.time()
    out = a.out.resolve()
    if out.exists() and any(out.iterdir()):
        print(f"refusing to write into non-empty {out}; use a clean output directory", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    ctx = Ctx()
    ctx.out, ctx.data_root = out, a.data_root.resolve()
    ctx.inp = Inputs(ctx.data_root)
    ctx.inp.read(Path(proc.__file__))
    ctx.inp.read(Path(__file__))
    ctx.manifest = ctx.inp.json(ctx.data_root / "manifest.json")
    tj = ctx.inp.json(REPO / "backend/content/targets.json")
    ctx.targets = {t["id"]: t for t in tj["targets"]}
    cases = {c: ctx.inp.json(REPO / f"backend/content/cases/{c}.json") for c in ("fair_comparison", "moving_neighbor")}
    tr = ctx.inp.json(REPO / "science/reviews/transfer-exercise/results.json")
    assert {k: v["frame_key"] for k, v in tr["frames"].items()} == WISE_KEYS
    ctx.wise = {ref: load_frame(ctx, "wise_0855", "frames", k) for ref, k in WISE_KEYS.items()}
    ctx.eps = {f["ref"]: load_frame(ctx, "epsilon_indi_b", "case-fair_comparison", f["frame_key"]) for f in cases["fair_comparison"]["frames"]}
    ctx.barn = {f["ref"]: load_frame(ctx, "barnards_star", "case-moving_neighbor", f["frame_key"]) for f in cases["moving_neighbor"]["frames"]}
    ctx.barn_pf = {ref: load_frame(ctx, "barnards_star", "frames", fr["key"]) for ref, fr in ctx.barn.items()}
    ctx.results = {}
    loaded = [("wise_0855/frames", fr) for fr in ctx.wise.values()] + [("epsilon_indi_b/case-fair_comparison", fr) for fr in ctx.eps.values()] \
        + [("barnards_star/case-moving_neighbor", fr) for fr in ctx.barn.values()] + [("barnards_star/frames", fr) for fr in ctx.barn_pf.values()]
    ctx.integrity = {"rule": "record provenance.sha256 == manifest.json sha256 == sha256(raw FITS bytes)",
                     "n": len(loaded), "n_all_equal": sum(1 for _, fr in loaded if fr["sha_all_equal"]),
                     "frames": [{"record": f"{d}/{fr['key']}", "all_equal": fr["sha_all_equal"]} for d, fr in loaded]}
    for name, fn in (("A", control_A), ("B", control_B), ("C", control_C), ("D", control_D), ("E", control_E)):
        t = time.time()
        fn(ctx)
        print(f"control {name}: {time.time() - t:.1f} s", flush=True)
    results = {
        "generator": "science/reviews/overnight-controls/run_controls.py",
        "status": "Deliberately chosen teaching counterexamples, not a representative survey. No photometry, astrometry, "
                  "detection test, learner study or AI benchmark. Deterministic mappings use tolerances, not statistics.",
        "processing_version": proc.PROCESSING_VERSION,
        "integrity": ctx.integrity,
        "controls": ctx.results,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1, default=float) + "\n")
    outputs = {}
    for p in sorted(out.iterdir()):
        if p.name == "manifest.json":
            continue
        b = p.read_bytes()
        outputs[p.name] = {"sha256": sha256(b), "bytes": len(b)}
    import astropy
    import PIL
    manifest = {
        "command": "python science/reviews/overnight-controls/run_controls.py --data-root <research/build_data> --out <clean dir>",
        "argv": [Path(sys.argv[0]).name] + ["--data-root", "<data_root>", "--out", out.name],
        "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_s": round(time.time() - t0, 1),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "astropy": astropy.__version__,
                        "pillow": PIL.__version__, "platform": platform.platform()},
        "inputs": dict(sorted(ctx.inp.items.items())),
        "outputs": outputs,
        "note": "Inputs are read only. data_root:raw/* FITS are retained cutouts (not committed). Output PNGs are derived views.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {len(outputs) + 1} files to {out} in {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
