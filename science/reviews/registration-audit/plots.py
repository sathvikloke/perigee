"""Two small static figures for the registration audit (Pillow only; no matplotlib
in the reviewer environment). Light surface, recessive axes, reference palette
slots in fixed order (blue, orange, aqua), text in text ink, legends present."""

from __future__ import annotations

import csv
import json
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SURFACE = (252, 252, 251)
INK = (11, 11, 11)
INK2 = (82, 81, 78)
GRID = (226, 225, 220)
SERIES = [(42, 120, 214), (235, 104, 52), (27, 175, 122)]


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _panel(dr, box, xmax, ymax, xlabel, title, xticks, yticks):
    x0, y0, x1, y1 = box
    f, ft = font(13), font(15)
    for t in yticks:
        y = y1 - (y1 - y0) * t / ymax
        dr.line([(x0, y), (x1, y)], fill=GRID, width=1)
        dr.text((x0 - 8, y), f"{t:g}", fill=INK2, font=f, anchor="rm")
    for t in xticks:
        x = x0 + (x1 - x0) * t / xmax
        dr.line([(x, y1), (x, y1 + 4)], fill=INK2, width=1)
        dr.text((x, y1 + 8), f"{t:g}", fill=INK2, font=f, anchor="mt")
    dr.line([(x0, y1), (x1, y1)], fill=INK2, width=1)
    dr.text((x0, y0 - 30), title, fill=INK, font=ft, anchor="ls")
    dr.text(((x0 + x1) / 2, y1 + 30), xlabel, fill=INK2, font=f, anchor="mt")


def _bars(dr, box, edges, stacks, xmax, ymax):
    """stacks: list of count arrays (bottom to top), one per series."""
    x0, y0, x1, y1 = box
    base = np.zeros(len(edges) - 1)
    for si, counts in enumerate(stacks):
        for i, c in enumerate(counts):
            if c <= 0:
                continue
            xa = x0 + (x1 - x0) * edges[i] / xmax + 1
            xb = x0 + (x1 - x0) * edges[i + 1] / xmax - 1
            ya = y1 - (y1 - y0) * (base[i] + c) / ymax
            yb = y1 - (y1 - y0) * base[i] / ymax - (2 if base[i] > 0 else 0)
            dr.rectangle([xa, min(ya, yb), xb, yb], fill=SERIES[si])
        base = base + counts


def _nice(m):
    """Smallest 'nice' axis maximum >= m with at most 5 intervals of 1/2/5 x 10^k."""
    m = max(m, 1)
    mag = 10 ** math.floor(math.log10(m))
    for k in (0.1, 0.2, 0.5, 1, 2, 5, 10):
        step = k * mag
        if math.ceil(m / step) <= 5:
            return math.ceil(m / step) * step
    return 10 * mag


def residual_plot(csv_path, out_path):
    rows = list(csv.DictReader(open(csv_path)))
    nat_ret = np.array([float(r["native_r_px"]) for r in rows if r["stage"] == "retained"])
    nat_assoc = np.array([float(r["native_r_px"]) for r in rows if r["stage"] == "association"])
    nat_pngw = np.array([float(r["native_r_px"]) for r in rows if r["stage"] == "png_window"])
    png = np.array([float(r["png_r_display_px"]) for r in rows if r["stage"] == "retained"])
    W, H = 1200, 560
    im = Image.new("RGB", (W, H), SURFACE)
    dr = ImageDraw.Draw(im)
    f = font(13)
    # panel A: native offsets of all SNR-eligible stars, split by what the legacy rule did
    edges = np.arange(0, 3.01, 0.1)
    st = [np.histogram(nat_ret, edges)[0], np.histogram(nat_pngw, edges)[0], np.histogram(nat_assoc, edges)[0]]
    ymax = _nice(max((st[0] + st[1] + st[2]).max(), 1) * 1.1)
    boxA = (80, 90, 560, 420)
    _panel(dr, boxA, 3.0, ymax, "native centroid - Gaia (native px; 1 px = 6.1-6.2\")",
           f"A. SNR-eligible Gaia stars (n={len(nat_ret) + len(nat_pngw) + len(nat_assoc)}), unique frames",
           [0, 0.5, 1, 1.5, 2, 2.5, 3], np.linspace(0, ymax, 6))
    _bars(dr, boxA, edges, st, 3.0, ymax)
    xc = boxA[0] + (boxA[2] - boxA[0]) * 1.0 / 3.0
    dr.line([(xc, boxA[1]), (xc, boxA[3])], fill=INK, width=1)
    dr.text((xc + 6, boxA[1] + 4), "legacy 1 px association cut", fill=INK, font=f, anchor="lt")
    lx = 80
    for i, (lab, n) in enumerate([("retained", len(nat_ret)), ("PNG window rejected", len(nat_pngw)),
                                  ("dropped by 1 px cut", len(nat_assoc))]):
        dr.rectangle([lx, 489, lx + 12, 501], fill=SERIES[i])
        txt = f"{lab} ({n})"
        dr.text((lx + 18, 495), txt, fill=INK, font=f, anchor="lm")
        lx += 30 + dr.textlength(txt, font=f)
    # panel B: PNG residuals of retained stars
    edges = np.arange(0, 6.01, 0.25)
    h = np.histogram(np.clip(png, 0, 5.999), edges)[0]
    ymax = _nice(max(h.max(), 1) * 1.1)
    boxB = (680, 90, 1160, 420)
    _panel(dr, boxB, 6.0, ymax, "PNG centroid - Gaia (display px; 1 px = 1.406\"; last bin includes > 6)",
           f"B. Retained matches on the published PNGs (n={len(png)})", [0, 1, 2, 3, 4, 5, 6], np.linspace(0, ymax, 6))
    _bars(dr, boxB, edges, [h], 6.0, ymax)
    for p, lab in ((50, "median"), (90, "p90")):
        v = float(np.percentile(png, p))
        x = boxB[0] + (boxB[2] - boxB[0]) * v / 6.0
        dr.line([(x, boxB[1]), (x, boxB[3])], fill=INK, width=1)
        dr.text((x + 5, boxB[1] + 4 + (0 if p == 50 else 18)), f"{lab} {v:.2f}", fill=INK, font=f, anchor="lt")
    dr.text((80, 535), "Panel B: selected matches only: not a global accuracy bound for all products.", fill=INK2, font=f, anchor="lm")
    im.save(out_path, optimize=True)


def negative_control_plot(json_path, out_path):
    neg = json.load(open(json_path))
    runs = neg["runs"]
    labels = list(dict.fromkeys(r["perturbation"] for r in runs))
    frames = list(dict.fromkeys(r["frame_key"] for r in runs))
    W, H = 1200, 600
    im = Image.new("RGB", (W, H), SURFACE)
    dr = ImageDraw.Draw(im)
    f, ft = font(13), font(15)
    x0, y0, x1, y1 = 290, 90, 1160, 380
    ymax = _nice(max(max(r["legacy_gaia_n_png"] for r in runs), 1) * 1.15)
    dr.text((x0, y0 - 40), "Negative control: legacy retained Gaia matches vs injected registration error", fill=INK, font=ft, anchor="ls")
    dr.text((x0, y0 - 20), "Lines: Gaia stars the legacy rule still uses. Text rows: verdicts, legacy acceptance 'registration' / new validator.",
            fill=INK2, font=f, anchor="ls")
    for t in np.linspace(0, ymax, 6):
        y = y1 - (y1 - y0) * t / ymax
        dr.line([(x0, y), (x1, y)], fill=GRID)
        dr.text((x0 - 8, y), f"{t:g}", fill=INK2, font=f, anchor="rm")
    dr.line([(x0, y1), (x1, y1)], fill=INK2)
    step = (x1 - x0) / len(labels)
    xs = [x0 + step * (i + 0.5) for i in range(len(labels))]
    for i, lab in enumerate(labels):
        dr.text((xs[i], y1 + 10), lab, fill=INK2, font=f, anchor="mt")
    dr.text((x0 - 50, (y0 + y1) / 2), "Gaia stars", fill=INK2, font=f, anchor="rm")
    for fi, fk in enumerate(frames):
        pts = []
        for i, lab in enumerate(labels):
            r = next(r for r in runs if r["frame_key"] == fk and r["perturbation"] == lab)
            pts.append((xs[i] + (fi - 1) * 6, y1 - (y1 - y0) * r["legacy_gaia_n_png"] / ymax))
        dr.line(pts, fill=SERIES[fi], width=2)
        for p in pts:
            dr.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], fill=SERIES[fi], outline=SURFACE, width=2)
        # verdict rows
        yy = y1 + 40 + fi * 44
        dr.rectangle([20, yy + 6, 32, yy + 18], fill=SERIES[fi])
        dr.text((38, yy + 12), fk, fill=INK, font=f, anchor="lm")
        for i, lab in enumerate(labels):
            r = next(r for r in runs if r["frame_key"] == fk and r["perturbation"] == lab)
            leg = "pass" if r["legacy_acceptance_check_one_registration"] else "FAIL"
            new = r["validator_verdict"]
            dr.text((xs[i], yy + 12), f"{leg} / {new}", fill=INK if new != "PASS" or lab == "identity" else INK2,
                    font=f, anchor="mm")
    dr.text((x0, H - 20), "Fixtures are derived (pixels moved vs the unchanged header) and kept separate from real-observation results.",
            fill=INK2, font=f, anchor="ls")
    im.save(out_path, optimize=True)
