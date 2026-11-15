"""Five-preset identity / coordinate audit (worker 11). Python 3 stdlib only.

Reads (never writes) backend/content/targets.json, research/build_data/manifest.json and
the shipped product records under backend/content/presets/**. Compares them with the
SIMBAD (CfA mirror) and Gaia DR3 snapshots cached in ./sources/*.csv, and expresses every
difference as a shift of the catalog-prediction marker in display pixels on the shipped
6 arcmin / 256 px grid (1.40625 arcsec per display px).

Independent of backend/data and tools/ingest: the space-motion propagation, the gnomonic
projection and the annual-parallax estimate are written out here.

Usage (repository root):  python3 science/reviews/targets/check_targets.py
Writes science/reviews/targets/results.json
"""

from __future__ import annotations

import csv
import glob
import io
import json
import math
import os
import statistics as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
MAS = math.pi / (180 * 3600 * 1000)
KMS_TO_PC_PER_YR = 1.0227121650537077e-6  # 1 km/s in pc / Julian year
PX = 1.40625  # arcsec per display px on the shipped grid


def read_csv(name):
    with open(os.path.join(SRC, name)) as f:
        return list(csv.DictReader(io.StringIO("".join(l for l in f if not l.startswith("#")))))


def fnum(v):
    return None if v in (None, "") else float(v)


# ------------------------------------------------------------------ astrometry


def unit(ra, dec):
    a, d = math.radians(ra), math.radians(dec)
    return (math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d))


def propagate(ra, dec, pmra, pmdec, plx, rv, t0, t1):
    """Rigorous linear space motion (what astropy apply_space_motion does), years = Julian."""
    a, d = math.radians(ra), math.radians(dec)
    dist = 1000.0 / plx  # pc
    u = unit(ra, dec)
    ea = (-math.sin(a), math.cos(a), 0.0)
    ed = (-math.sin(d) * math.cos(a), -math.sin(d) * math.sin(a), math.cos(d))
    vt_a, vt_d = pmra * MAS * dist, pmdec * MAS * dist  # pc / yr
    vr = (rv or 0.0) * KMS_TO_PC_PER_YR
    dt = t1 - t0
    r = [dist * u[i] + dt * (vt_a * ea[i] + vt_d * ed[i] + vr * u[i]) for i in range(3)]
    ra1 = math.degrees(math.atan2(r[1], r[0])) % 360.0
    dec1 = math.degrees(math.atan2(r[2], math.hypot(r[0], r[1])))
    return ra1, dec1


def mjd_to_jyear(mjd):
    return 2000.0 + (mjd - 51544.5) / 365.25


def offset_arcsec(ra1, dec1, ra0, dec0):
    """(east, north) offset of point 1 from point 0, arcsec, gnomonic about point 0."""
    a, d, a0, d0 = map(math.radians, (ra1, dec1, ra0, dec0))
    cosc = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    xi = math.cos(d) * math.sin(a - a0) / cosc
    eta = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / cosc
    return math.degrees(xi) * 3600, math.degrees(eta) * 3600


def sep_arcsec(ra1, dec1, ra0, dec0):
    e, n = offset_arcsec(ra1, dec1, ra0, dec0)
    return math.hypot(e, n)


def display_xy(ra, dec, reg):
    e, n = offset_arcsec(ra, dec, reg["center_ra_deg"], reg["center_dec_deg"])
    s = reg["fov_arcmin"] * 60.0 / reg["width"]
    return reg["width"] / 2.0 - e / s, reg["height"] / 2.0 - n / s


def sun_geocentric_au(mjd):
    """Low-precision Sun (Astronomical Almanac, ~0.01 deg): equatorial geocentric xyz in AU."""
    n = mjd - 51544.5
    L = math.radians((280.460 + 0.9856474 * n) % 360)
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2 * g)
    R = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    return (R * math.cos(lam), R * math.cos(eps) * math.sin(lam), R * math.sin(eps) * math.sin(lam))


def annual_parallax_arcsec(ra, dec, plx_mas, mjd):
    """(east, north) apparent shift from annual parallax for a geocentric observer.
    SPHEREx is in low Earth orbit (<0.0001 AU from the geocentre), so this is adequate."""
    s = sun_geocentric_au(mjd)  # = -(Earth barycentric), to ~0.01 AU
    u = unit(ra, dec)
    a, d = math.radians(ra), math.radians(dec)
    ea = (-math.sin(a), math.cos(a), 0.0)
    ed = (-math.sin(d) * math.cos(a), -math.sin(d) * math.sin(a), math.cos(d))
    sdotu = sum(s[i] * u[i] for i in range(3))
    du = [s[i] - sdotu * u[i] for i in range(3)]  # apparent shift direction is toward the Sun's projection
    p = plx_mas / 1000.0
    return p * sum(du[i] * ea[i] for i in range(3)), p * sum(du[i] * ed[i] for i in range(3))


# ------------------------------------------------------------------ inputs


def load_products():
    recs = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "backend/content/presets/*/*/*.json"))):
        if os.path.basename(p) == "frames.json":
            continue
        with open(p) as f:
            r = json.load(f)
        if "marker" not in r:
            continue
        preset = p.split(os.sep)[-3]
        recs.setdefault(preset, []).append((os.path.relpath(p, ROOT), r))
    return recs


def main():
    with open(os.path.join(ROOT, "backend/content/targets.json")) as f:
        targets = {t["id"]: t for t in json.load(f)["targets"]}
    with open(os.path.join(ROOT, "research/build_data/manifest.json")) as f:
        manifest = {t["id"]: t for t in json.load(f)["targets"]}
    simbad = {r["queried"]: r for r in read_csv("simbad_basic.csv")}
    gaia = {r["source_id"]: r for r in read_csv("gaia_ids.csv")}
    rwaur_gaia = read_csv("gaia_rwaur.csv")
    products = load_products()
    out = {"targets": {}}

    for tid, t in targets.items():
        cp, am, qc = t["catalog_position"], t["astrometry"], t["query_center"]
        res = {}
        s = simbad[t["simbad_name"]]
        # 1. identity / catalog values vs SIMBAD today
        res["simbad_main_id"] = s["main_id"]
        res["simbad_vs_repo"] = {
            "ra_arcsec": sep_arcsec(float(s["ra"]), float(s["dec"]), cp["ra_deg"], cp["dec_deg"]),
            "pmra_masyr": float(s["pmra"]) - am["pm_ra_cosdec_masyr"],
            "pmdec_masyr": float(s["pmdec"]) - am["pm_dec_masyr"],
            "plx_mas": float(s["plx_value"]) - am["parallax_mas"],
            "rv_simbad": fnum(s["rvz_radvel"]), "rv_repo": am["radial_velocity_kms"],
            "rv_manifest": manifest[tid]["radial_velocity_kms"],
            "coo_bibcode": s["coo_bibcode"], "pm_bibcode": s["pm_bibcode"], "coo_qual": s["coo_qual"],
            "repo_astrometry_reference": cp["astrometry_reference"],
        }
        # 2. query center = propagation to stated epoch?
        args = (cp["ra_deg"], cp["dec_deg"], am["pm_ra_cosdec_masyr"], am["pm_dec_masyr"], am["parallax_mas"])
        qra, qdec = propagate(*args, am["radial_velocity_kms"], cp["epoch_jyear"], qc["epoch_jyear"])
        qra_m, qdec_m = propagate(*args, manifest[tid]["radial_velocity_kms"], cp["epoch_jyear"], qc["epoch_jyear"])
        res["query_center_check"] = {
            "recomputed_minus_repo_arcsec": sep_arcsec(qra, qdec, qc["ra_deg"], qc["dec_deg"]),
            "recomputed_with_manifest_rv_minus_repo_arcsec": sep_arcsec(qra_m, qdec_m, qc["ra_deg"], qc["dec_deg"]),
            "j2000_to_query_center_arcsec": sep_arcsec(qc["ra_deg"], qc["dec_deg"], cp["ra_deg"], cp["dec_deg"]),
            "total_pm_masyr": math.hypot(am["pm_ra_cosdec_masyr"], am["pm_dec_masyr"]),
        }
        # 3. products: registration centre, fov, marker
        recs = products.get(tid, [])
        bad_center, bad_fov, dm, frames = [], [], [], []
        for path, r in recs:
            reg = r["registration"]
            if (reg["center_ra_deg"], reg["center_dec_deg"]) != (qc["ra_deg"], qc["dec_deg"]):
                bad_center.append(path)
            if reg["fov_arcmin"] != t["default_fov_arcmin"]:
                bad_fov.append(path)
            mjd = r["mjd"]
            pra, pdec = propagate(*args, manifest[tid]["radial_velocity_kms"], cp["epoch_jyear"], mjd_to_jyear(mjd))
            x, y = display_xy(pra, pdec, reg)
            dm.append(math.hypot(x - r["marker"]["x"], y - r["marker"]["y"]))
            frames.append((path, r, reg, mjd, pra, pdec))
        res["products"] = {
            "n_records": len(recs),
            "registration_center_equals_query_center": not bad_center, "mismatched_center": bad_center,
            "fov_equals_default": not bad_fov,
            "marker_recomputed_max_diff_display_px": max(dm) if dm else None,
            "mjd_range": [min(f[3] for f in frames), max(f[3] for f in frames)] if frames else None,
            "status_counts": {k: sum(1 for _, r in recs if r["quality"]["status"] == k and "/frames/" in _)
                              for k in ("clear", "flagged", "not_covered")},
        }

        # 4. alternatives -> marker shift on shipped frames
        def shift_stats(alt_fn):
            d = []
            for path, r, reg, mjd, pra, pdec in frames:
                ara, adec = alt_fn(mjd)
                e, n = offset_arcsec(ara, adec, pra, pdec)
                d.append(math.hypot(e, n) / PX)
            return {"median_display_px": st.median(d), "max_display_px": max(d), "min_display_px": min(d)}

        alts = {}
        gid = {"barnards_star": "4472832130942575872", "epsilon_indi_b": "6412596012146801152",
               "r_draconis": "1648328016354496384"}.get(tid)
        if gid:
            g = gaia[gid]
            gargs = (float(g["ra"]), float(g["dec"]))
            grv = fnum(g["radial_velocity"])
            alts["gaia_dr3_own_row_from_2016"] = shift_stats(lambda mjd: propagate(
                *gargs, float(g["pmra"]), float(g["pmdec"]), float(g["parallax"]), grv, 2016.0, mjd_to_jyear(mjd)))
            alts["gaia_dr3_ruwe"] = float(g["ruwe"])
        if tid == "epsilon_indi_b":
            g = gaia[gid]
            for label, pm in {"pm_2016ApJS..224...36K_(AllWISE_motion_survey)": (4003.2, -2490.6),
                              "pm_2018MNRAS.481.3548S_(PARSEC)": (4004.97, -2575.05)}.items():
                alts[label + "_pivot_gaia_2016"] = shift_stats(lambda mjd, pm=pm: propagate(
                    float(g["ra"]), float(g["dec"]), pm[0], pm[1], float(g["parallax"]), None, 2016.0, mjd_to_jyear(mjd)))
        if tid == "wise_0855":
            pm19 = (-8118.9, 679.3)  # 2019ApJS..240...19K, the other SIMBAD mesPM entry with a small error
            for pivot in (2000.0, 2015.405):
                def alt(mjd, pivot=pivot):
                    pra0, pdec0 = propagate(*args, None, 2000.0, pivot)
                    return propagate(pra0, pdec0, pm19[0], pm19[1], am["parallax_mas"], None, pivot, mjd_to_jyear(mjd))
                alts[f"pm_2019ApJS..240...19K_pivot_{pivot}"] = shift_stats(alt)
        if tid == "rw_aurigae":
            for g in rwaur_gaia:
                if float(g["sep_arcsec"]) > 3:
                    continue
                alts[f"gaia_dr3_{g['source_id']}_G{float(g['phot_g_mean_mag']):.2f}_ruwe{float(g['ruwe']):.1f}"] = shift_stats(
                    lambda mjd, g=g: propagate(float(g["ra"]), float(g["dec"]), float(g["pmra"]), float(g["pmdec"]),
                                               float(g["parallax"]), None, 2016.0, mjd_to_jyear(mjd)))
        res["alternatives_marker_shift"] = alts

        # 5. annual parallax (not modeled) on the shipped frames
        pl = [math.hypot(*annual_parallax_arcsec(f[4], f[5], am["parallax_mas"], f[3])) / PX for f in frames]
        res["annual_parallax_not_modeled_display_px"] = {"median": st.median(pl), "max": max(pl)} if pl else None

        # 6. WISE 0855 challenge coordinate
        cc = t.get("challenge_supplied_coordinate")
        if cc:
            best = min(((ep, sep_arcsec(cc["ra_deg"], cc["dec_deg"], *propagate(*args, None, 2000.0, ep)))
                        for ep in [2009.0 + i * 0.01 for i in range(301)]), key=lambda x: x[1])
            sx = [sep_arcsec(cc["ra_deg"], cc["dec_deg"], f[4], f[5]) for f in frames]
            res["challenge_coordinate"] = {
                "sexagesimal_check_arcsec": sep_arcsec(cc["ra_deg"], cc["dec_deg"],
                                                       (8 + 55 / 60 + 10.831 / 3600) * 15, -(7 + 14 / 60 + 42.53 / 3600)),
                "sep_from_catalog_propagation_at_2010.5_arcsec": sep_arcsec(
                    cc["ra_deg"], cc["dec_deg"], *propagate(*args, None, 2000.0, 2010.5)),
                "closest_epoch_jyear": best[0], "closest_sep_arcsec": best[1],
                "sep_from_query_center_arcsec": sep_arcsec(cc["ra_deg"], cc["dec_deg"], qc["ra_deg"], qc["dec_deg"]),
                "sep_from_shipped_markers_arcsec": [min(sx), max(sx)],
                "min_fov_arcmin_to_contain_object_on_shipped_epochs": 2 * max(
                    max(abs(c) for c in offset_arcsec(f[4], f[5], cc["ra_deg"], cc["dec_deg"])) for f in frames) / 60,
            }
            # Field star that the WISE 0855 track approaches (from the acceptance Gaia cache)
            with open(os.path.join(ROOT, "science/reviews/acceptance/gaia/wise_0855.csv")) as f:
                nb = [g for g in csv.DictReader(f) if g["source_id"] == "5756956644387831296"][0]

            def nb_at(jy):
                return (float(nb["ra"]) + float(nb["pmra"]) * (jy - 2016) / 3.6e6 / math.cos(math.radians(float(nb["dec"]))),
                        float(nb["dec"]) + float(nb["pmdec"]) * (jy - 2016) / 3.6e6)
            ns = [sep_arcsec(*nb_at(mjd_to_jyear(f[3])), f[4], f[5]) for f in frames]
            track = [(sep_arcsec(*nb_at(jy), *propagate(*args, None, 2000.0, jy)), jy)
                     for jy in [2025.0 + i * 0.005 for i in range(401)]]
            res["neighbour_gaia_dr3_5756956644387831296"] = {
                "G": float(nb["phot_g_mean_mag"]),
                "sep_from_shipped_markers_arcsec": [min(ns), max(ns)],
                "closest_approach_arcsec": min(track)[0], "closest_approach_jyear": min(track)[1],
                "sep_at_2026.75_arcsec": sep_arcsec(*nb_at(2026.75), *propagate(*args, None, 2000.0, 2026.75)),
            }
            # CatWISE2020 entries (apparent-motion fits at MJD 57170)
            rows = []
            with open(os.path.join(SRC, "catwise2020_wise0855.tbl")) as f:
                for l in f:
                    if l.lstrip().startswith("J0855"):
                        p = l.split()
                        if abs(float(p[10])) > 5:  # pmra arcsec/yr: keep the fast-moving fragments only
                            rows.append((p[0], float(p[8]), float(p[9]), float(p[10]), float(p[11])))
            ref = propagate(*args, None, 2000.0, 2015.405)
            res["catwise2020_fragments_vs_repo_at_2015.405"] = [
                {"name": n, "sep_arcsec": sep_arcsec(ra_, de_, *ref), "pmra_asyr": pa, "pmdec_asyr": pd}
                for n, ra_, de_, pa, pd in rows]
        out["targets"][tid] = res

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    for tid, res in out["targets"].items():
        print(f"\n== {tid}")
        print(json.dumps(res, indent=1, default=float)[:4000])


if __name__ == "__main__":
    main()
