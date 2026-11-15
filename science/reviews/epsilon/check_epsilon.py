"""Epsilon Indi B `fair_comparison` case review (parallel worker 09).

Reads the three original FITS cutouts (read only) and the committed case
products, and writes results.json + contact_sheet.png next to this file.

Independent of backend/data and tools/ingest. Geometry, wavelength and Gaia
helpers are reused from science/reviews/acceptance/check_acceptance.py, which
is itself independent of the processor.

What it checks, per frame A/B/C:
  * OBSID, DETECTOR, DATE-AVG, MJD-AVG straight from the IMAGE header;
  * the catalog prediction (targets.json astrometry, astropy apply_space_motion
    to MJD-AVG) and the wavelength there (key-W WCS and a hand-written -TAB lookup);
  * the r = 2.5 native px flag screen, decoded from MSKN/MSKM;
  * where Epsilon Indi A (Gaia DR3 6412595290592307840) falls on the 6' grid;
  * Gaia DR3 field stars: which centroid cleanly (native image), and how they
    move on the published PNGs between frames;
  * a within-frame ordering against one reference field star (Gaia DR3
    6412596458823395328, G = 13.0, upper left): a crude background-subtracted
    3x3 native-pixel box sum, and the number of display pixels clipped to white
    near each. This only checks the direction of the visual impression ("which
    looks brighter in this frame"). It is not photometry and is not learner text;
  * a smooth background trend across the field (display grey levels and
    native MJy/sr) and the HALO flag census, to describe the uneven background.

Usage (repository root):
    .venv/bin/python science/reviews/epsilon/check_epsilon.py \
        --data-root "/path/to/research/build_data"
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import warnings
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image, ImageDraw

warnings.simplefilter("ignore")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_spec = importlib.util.spec_from_file_location("acc", REPO / "science/reviews/acceptance/check_acceptance.py")
acc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acc)

CASE = REPO / "backend/content/cases/fair_comparison.json"
PROD = REPO / "backend/content/presets/epsilon_indi_b/case-fair_comparison"
FRAMES = [("A", "2026W18_1A_0516_1_D3"), ("B", "2026W39_2A_0597_4_D3"), ("C", "2026W18_1A_0516_1_D6")]
APERTURE_R = 2.5
ADVERSE_EXEMPT = {"SOURCE", "FULLSAMPLE"}
# Isolated bright display spots a blinking learner may notice (found by eye on the
# contact sheet); their native flags are recorded per frame in results.json.
REF_STAR = 6412596458823395328  # Gaia DR3, G = 13.0, upper left of the grid
SPOTS = {"A_next_to_target": (144, 138), "C_lower_right": (192, 232)}

# Gaia DR3 6412595290592307840 (eps Ind A), epoch J2016.0; same values as the acceptance review
EPS_A = SkyCoord(ra=330.8724078795965 * u.deg, dec=-56.79725466122902 * u.deg,
                 pm_ra_cosdec=3966.6605387484133 * u.mas / u.yr, pm_dec=-2536.1919868044724 * u.mas / u.yr,
                 distance=(1000 / 274.8431415216296) * u.pc, radial_velocity=-40.4267 * u.km / u.s,
                 obstime=Time(2016.0, format="jyear"))


def raw_path(raw_dir: Path, key: str) -> Path:
    obs, det = key.rsplit("_D", 1)
    hits = sorted(raw_dir.glob(f"level2_{obs}D{det}_spx_*.fits"))
    assert len(hits) == 1, (key, hits)
    return hits[0]


def flag_screen(fl, fh, img, var, x, y):
    names = {int(k[4:]): fh[k].strip() for k in fh if k.startswith("MSKN")}
    for b in names:
        mk = f"MSKM{b:04d}"
        if mk in fh:
            assert int(fh[mk]) == 1 << b, mk
    ny, nx = fl.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    ap = (xx - x) ** 2 + (yy - y) ** 2 <= APERTURE_R ** 2
    counts, adverse = {}, np.zeros(ap.sum(), bool)
    vals = fl[ap]
    for b, n in names.items():
        hit = (vals & (1 << b)) != 0
        if hit.any():
            counts[n] = int(hit.sum())
            if n not in ADVERSE_EXEMPT:
                adverse |= hit
    nonfinite = ~np.isfinite(img[ap]) | ~np.isfinite(var[ap]) | (var[ap] <= 0)
    bad = adverse | nonfinite
    return {"screened": int(ap.sum()), "adverse": int(bad.sum()), "nonfinite": int(nonfinite.sum()),
            "flag_counts": counts, "status": "flagged" if bad.any() else "clear"}, names


def box_sum(img, x, y):
    ix, iy = int(round(x)), int(round(y))
    bg = np.nanmedian(img[iy - 6:iy + 7, ix - 6:ix + 7])
    return float(np.nansum(img[iy - 1:iy + 2, ix - 1:ix + 2] - bg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    a = ap.parse_args()
    raw_dir = Path(a.data_root) / "raw" / "epsilon_indi_b"
    case = json.loads(CASE.read_text())
    cf = {f["ref"]: f for f in case["frames"]}
    targets = json.loads((REPO / "backend/content/targets.json").read_text())
    t = next(x for x in targets["targets"] if x["id"] == "epsilon_indi_b")
    tgt = {"ra_j2000_deg": t["catalog_position"]["ra_deg"], "dec_j2000_deg": t["catalog_position"]["dec_deg"],
           "pm_ra_cosdec_masyr": t["astrometry"]["pm_ra_cosdec_masyr"], "pm_dec_masyr": t["astrometry"]["pm_dec_masyr"],
           "parallax_mas": t["astrometry"]["parallax_mas"], "radial_velocity_kms": None,
           "reference_epoch_jyear": t["catalog_position"]["epoch_jyear"]}
    q = t["query_center"]
    gaia = acc.load_gaia("epsilon_indi_b")
    res = {"frames": {}, "notes": []}
    pngs = {}
    for ref, key in FRAMES:
        rec = json.loads((PROD / f"{key}.json").read_text())
        rp = raw_path(raw_dir, key)
        sha = hashlib.sha256(rp.read_bytes()).hexdigest()
        with fits.open(rp) as h:
            ih, fh = h["IMAGE"].header, h["FLAGS"].header
            img = h["IMAGE"].data.astype(float)
            var = h["VARIANCE"].data.astype(float)
            fl = h["FLAGS"].data.astype(np.int64)
            zodi = h["ZODI"].data.astype(float)
            mjd = float(ih["MJD-AVG"])
            ra, dec, _, _ = acc.predict(tgt, mjd)
            cw = WCS(ih)
            x, y = (float(v) for v in cw.all_world2pix(ra, dec, 0))
            wl, bw = acc.wave_astropy(ih, h, x, y)
            wl2, bw2, _ = acc.wave_manual(ih, h, x, y)
            screen, names = flag_screen(fl, fh, img, var, x, y)
            halo_bit = next(b for b, n in names.items() if n == "HALO")
            halo = (fl & (1 << halo_bit)) != 0
            # Eps Ind A
            pa = EPS_A.apply_space_motion(new_obstime=Time(mjd, format="mjd"))
            ax, ay = acc.sky_to_display(pa.ra.deg, pa.dec.deg, q["ra_deg"], q["dec_deg"], 6.0, 256)
            sep_a = SkyCoord(ra * u.deg, dec * u.deg).separation(pa).arcmin
            # Gaia field stars in the native image
            stars = []
            for s in gaia:
                sra, sdec = acc.gaia_at(s, mjd)
                if SkyCoord(sra * u.deg, sdec * u.deg).separation(SkyCoord(ra * u.deg, dec * u.deg)).arcsec < 20:
                    continue
                gx, gy = (float(v) for v in cw.all_world2pix(sra, sdec, 0))
                c = acc.native_centroid(img, gx, gy)
                ok = c is not None and math.hypot(c[0] - gx, c[1] - gy) <= 1.0
                dx, dy = acc.sky_to_display(sra, sdec, q["ra_deg"], q["dec_deg"], 6.0, 256)
                stars.append({"source_id": int(s["source_id"]), "G": s["phot_g_mean_mag"], "display": [float(dx), float(dy)],
                              "native_centroid_ok": bool(ok), "peak_over_mad": None if c is None else c[2]})
            # within-frame ordering against the reference star (not photometry)
            ref_star = next(s for s in gaia if int(s["source_id"]) == REF_STAR)
            rra, rdec = acc.gaia_at(ref_star, mjd)
            rx, ry = (float(v) for v in cw.all_world2pix(rra, rdec, 0))
            boxes = [box_sum(img, x, y), box_sum(img, rx, ry)]
            # background trend, native MJy/sr: east (left on display) vs west (right) halves
            fin = np.isfinite(img)
            cel = cw.all_pix2world(*np.meshgrid(np.arange(img.shape[1]), np.arange(img.shape[0])), 0)
            gx_, _ = acc.sky_to_display(cel[0], cel[1], q["ra_deg"], q["dec_deg"], 6.0, 256)
            west = (gx_ > 128) & fin
            east = (gx_ <= 128) & fin
            med_w, med_e = float(np.nanmedian(img[west])), float(np.nanmedian(img[east]))
            mad_all = float(np.nanmedian(np.abs(img[fin] - np.nanmedian(img[fin]))) * 1.4826)
            zw, ze = float(np.nanmedian(zodi[west])), float(np.nanmedian(zodi[east]))
            halo_w, halo_e = int((halo & (gx_ > 128)).sum()), int((halo & (gx_ <= 128)).sum())
            spots = {}
            for name, (sx, sy) in SPOTS.items():
                s_ra, s_dec = acc.inv_gnomonic(-(sx - 128) * math.radians(0.1) / 256, (128 - sy) * math.radians(0.1) / 256,
                                               q["ra_deg"], q["dec_deg"])
                nx_, ny_ = (int(round(float(v))) for v in cw.all_world2pix(s_ra, s_dec, 0))
                spots[name] = {"native_xy": [nx_, ny_], "native_px_from_target": math.hypot(nx_ - x, ny_ - y),
                               "flags": sorted(n for b, n in names.items() if fl[ny_, nx_] & (1 << b)),
                               "value_MJysr": float(img[ny_, nx_]), "local_median_MJysr": float(np.nanmedian(img[ny_ - 3:ny_ + 4, nx_ - 3:nx_ + 4]))}
        im = Image.open(PROD / f"{key}.png")
        g = np.asarray(im)[:, :, 0].astype(int)
        al = np.asarray(im)[:, :, 1]
        pngs[ref] = (g, al, rec)
        rd = next(st for st in stars if st["source_id"] == REF_STAR)["display"]

        def white(px, py, h=6):
            return int((g[int(py) - h:int(py) + h, int(px) - h:int(px) + h] == 255).sum())
        okp = al > 0
        cols = np.arange(256)[None, :].repeat(256, 0)
        res["frames"][ref] = {
            "frame_key": key,
            "raw_file": rp.name,
            "sha256": sha,
            "sha256_matches_case": sha == cf[ref]["sha256_of_retained_cutout"],
            "OBSID": ih["OBSID"], "DETECTOR": int(ih["DETECTOR"]),
            "DATE-AVG": ih["DATE-AVG"], "MJD-AVG": mjd, "TIMESYS": ih.get("TIMESYS"),
            "date_matches_case": ih["DATE-AVG"] == cf[ref]["observed_at_utc"],
            "predicted_radec": [ra, dec], "native_xy": [x, y],
            "wavelength_um": wl, "bandwidth_um": bw, "wavelength_um_tab": wl2,
            "case_wavelength_um": cf[ref]["wavelength_um"], "product_wavelength_um": rec["wavelength_um"],
            "screen": screen, "product_status": rec["quality"]["status"],
            "marker_product": [rec["marker"]["x"], rec["marker"]["y"]],
            "marker_independent": [float(v) for v in acc.sky_to_display(ra, dec, q["ra_deg"], q["dec_deg"], 6.0, 256)],
            "stretch": {k: rec["display_scale"][k] for k in ("mode", "low", "high")},
            "eps_ind_a": {"display_xy": [float(ax), float(ay)], "sep_from_eps_ind_b_arcmin": float(sep_a),
                          "px_beyond_right_edge": float(ax - 256)},
            "spots": spots,
            "gaia_field_stars": stars,
            "gaia_clean_centroids": sum(s["native_centroid_ok"] for s in stars),
            "ordering_vs_reference_star": {
                "reference_star": REF_STAR,
                "refstar_over_target_3x3_box": boxes[1] / boxes[0],
                "note": "crude box sum ratio for direction only; not photometry",
                "png_white_px_target": white(rec["marker"]["x"], rec["marker"]["y"]),
                "png_white_px_reference_star": white(*rd)},
            "background": {"native_median_west_minus_east_MJysr": med_w - med_e, "native_noise_mad_MJysr": mad_all,
                           "west_minus_east_over_noise": (med_w - med_e) / mad_all,
                           "zodi_model_west_minus_east_MJysr": zw - ze,
                           "png_grey_median_right_third": float(np.median(g[okp & (cols >= 171)])),
                           "png_grey_median_left_third": float(np.median(g[okp & (cols < 85)])),
                           "halo_flag_pixels_west": halo_w, "halo_flag_pixels_east": halo_e},
        }

    # field stars and marker on the published PNGs (what the learner sees)
    fA = res["frames"]["A"]
    moves = {}
    for ref in ("B", "C"):
        shifts = []
        for sA in fA["gaia_field_stars"]:
            sX = next(s for s in res["frames"][ref]["gaia_field_stars"] if s["source_id"] == sA["source_id"])
            if not (sA["native_centroid_ok"] and sX["native_centroid_ok"]):
                continue
            ca = acc.png_centroid(pngs["A"][0], pngs["A"][1], *sA["display"], half=4)
            cx = acc.png_centroid(pngs[ref][0], pngs[ref][1], *sX["display"], half=4)
            if ca and cx:
                shifts.append([sA["source_id"], cx[0] - ca[0], cx[1] - ca[1]])
        mA, mX = fA["marker_product"], res["frames"][ref]["marker_product"]
        moves[f"A_to_{ref}"] = {
            "marker_dx_px": mX[0] - mA[0], "marker_dy_px": mX[1] - mA[1],
            "marker_px": math.hypot(mX[0] - mA[0], mX[1] - mA[1]),
            "marker_arcsec": math.hypot(mX[0] - mA[0], mX[1] - mA[1]) * 1.40625,
            "field_star_png_shifts": shifts,
            "field_star_median_dx_dy": None if not shifts else [float(np.median([s[1] for s in shifts])), float(np.median([s[2] for s in shifts]))],
            "field_star_max_abs_component": None if not shifts else float(max(max(abs(s[1]), abs(s[2])) for s in shifts)),
        }
    res["moves"] = moves
    # glow centre at the marker on the PNG (visual proxy, as in the Barnard review)
    glow = {}
    for ref in ("A", "B", "C"):
        g, al, rec = pngs[ref]
        c = acc.png_centroid(g, al, rec["marker"]["x"], rec["marker"]["y"], half=5)
        glow[ref] = None if c is None else [c[0] - rec["marker"]["x"], c[1] - rec["marker"]["y"]]
    res["glow_minus_marker_px"] = glow
    out = HERE / "results.json"
    out.write_text(json.dumps(res, indent=1, default=float) + "\n")
    contact_sheet(pngs, res)
    for ref in ("A", "B", "C"):
        f = res["frames"][ref]
        print(ref, f["frame_key"], f["DATE-AVG"], round(f["wavelength_um"], 5), round(f["bandwidth_um"], 4),
              f["screen"]["status"], f"{f['screen']['adverse']}/{f['screen']['screened']}",
              "ref/target", round(f["ordering_vs_reference_star"]["refstar_over_target_3x3_box"], 2),
              "white px t/ref", f["ordering_vs_reference_star"]["png_white_px_target"], f["ordering_vs_reference_star"]["png_white_px_reference_star"],
              "gaia_ok", f["gaia_clean_centroids"], "W-E/noise", round(f["background"]["west_minus_east_over_noise"], 2),
              "EpsA x", round(f["eps_ind_a"]["display_xy"][0]), "y", round(f["eps_ind_a"]["display_xy"][1]))
    print(json.dumps(moves, indent=1, default=float)[:3000])
    print("glow-marker", glow)


def contact_sheet(pngs, res, zoom_half=24, zoom=4):
    """Top: full 256 px grids (2x). Bottom: 4x zoom on the marker. Marker = magenta
    circle/cross (catalog prediction). Green ticks = Gaia stars that centroid
    cleanly in A. Yellow box = isolated adverse-flagged pixel. Transparent pixels shown dark blue. Arrow = direction to Eps Ind A."""
    W = 512
    pad = 8
    sheet = Image.new("RGB", (3 * W + 4 * pad, W + 3 * pad + 40 + 2 * zoom_half * zoom), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    labels = {"A": "A  2026-04-29  2.323 um  shared stretch", "B": "B  2026-09-27  2.322 um  shared stretch",
              "C": "C  2026-04-29  4.940 um  own stretch"}
    for k, ref in enumerate(("A", "B", "C")):
        g, al, rec = pngs[ref]
        rgb = np.stack([g, g, g], -1).astype(np.uint8)
        rgb[al == 0] = (0, 0, 70)
        full = Image.fromarray(rgb).resize((W, W), Image.NEAREST)
        fd = ImageDraw.Draw(full)
        mx, my = rec["marker"]["x"] * 2, rec["marker"]["y"] * 2
        fd.ellipse([mx - 18, my - 18, mx + 18, my + 18], outline=(255, 0, 255), width=2)
        for s in res["frames"]["A"]["gaia_field_stars"]:
            if s["native_centroid_ok"]:
                sx, sy = s["display"][0] * 2, s["display"][1] * 2
                fd.line([sx - 16, sy, sx - 8, sy], fill=(0, 220, 0), width=2)
                fd.line([sx, sy + 8, sx, sy + 16], fill=(0, 220, 0), width=2)
        for name, (sx, sy) in SPOTS.items():
            if name.startswith(ref):
                fd.rectangle([sx * 2 - 14, sy * 2 - 14, sx * 2 + 14, sy * 2 + 14], outline=(255, 220, 0), width=2)
        # arrow toward Eps Ind A (off the right edge)
        ay = res["frames"][ref]["eps_ind_a"]["display_xy"][1] * 2
        fd.line([W - 60, ay, W - 6, ay], fill=(255, 170, 0), width=3)
        fd.polygon([(W - 4, ay), (W - 16, ay - 7), (W - 16, ay + 7)], fill=(255, 170, 0))
        fd.text((W - 110, ay - 20), "Eps Ind A ->", fill=(255, 170, 0))
        x0 = pad + k * (W + pad)
        sheet.paste(full, (x0, pad + 20))
        d.text((x0, pad + 4), labels[ref], fill=(230, 230, 230))
        cx, cy = int(round(rec["marker"]["x"])), int(round(rec["marker"]["y"]))
        crop = rgb[cy - zoom_half:cy + zoom_half, cx - zoom_half:cx + zoom_half]
        z = Image.fromarray(crop).resize((2 * zoom_half * zoom, 2 * zoom_half * zoom), Image.NEAREST)
        zd = ImageDraw.Draw(z)
        zx = (rec["marker"]["x"] - (cx - zoom_half)) * zoom
        zy = (rec["marker"]["y"] - (cy - zoom_half)) * zoom
        zd.line([zx - 30, zy, zx - 12, zy], fill=(255, 0, 255), width=2)
        zd.line([zx + 12, zy, zx + 30, zy], fill=(255, 0, 255), width=2)
        zd.line([zx, zy - 30, zx, zy - 12], fill=(255, 0, 255), width=2)
        zd.line([zx, zy + 12, zx, zy + 30], fill=(255, 0, 255), width=2)
        # fixed guide at A's marker
        ga = pngs["A"][2]["marker"]
        gx = (ga["x"] - (cx - zoom_half)) * zoom
        gy = (ga["y"] - (cy - zoom_half)) * zoom
        zd.line([0, gy, 2 * zoom_half * zoom, gy], fill=(0, 200, 0), width=1)
        zd.line([gx, 0, gx, 2 * zoom_half * zoom], fill=(0, 200, 0), width=1)
        sheet.paste(z, (x0 + (W - z.width) // 2, 2 * pad + W + 40))
        d.text((x0, 2 * pad + W + 24), f"{ref}: 4x zoom, magenta = prediction, green = A's marker", fill=(200, 200, 200))
    sheet.save(HERE / "contact_sheet.png", optimize=True)


if __name__ == "__main__":
    main()
