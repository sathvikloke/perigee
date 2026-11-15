#!/usr/bin/env python3
"""Generate data-derived figures, compile LaTeX, and validate the report PDF."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "perigee-report.tex"
GENERATED = HERE / "generated"
BUILD = HERE / "build"
NAMES = ["Sathvik Loke", "Sagar Raut", "Akshobya Rao", "Aditya Raut",
         "Suhrit Bestavemula", "Neeraj Movva"]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def figures():
    GENERATED.mkdir(exist_ok=True)
    case = json.loads((ROOT / "backend/content/cases/fair_comparison.json").read_text())
    panels = []
    for f in case["frames"]:
        date = {"A": "29 Apr 2026", "B": "27 Sep 2026", "C": "29 Apr 2026"}[f["ref"]]
        path = "../../backend/content/presets/epsilon_indi_b/case-fair_comparison/" + f["frame_key"] + ".png"
        panels.append(r"\observation{.31}{" + path + "}{" + f["ref"] + ": " + date + r"; " + f'{f["wavelength_um"]:.4f}' + r"\,\micron}")
    (GENERATED / "epsilon-panels.tex").write_text(r"\hfill".join(panels) + "\n")

    table = ROOT / "science/reviews/registration-audit/results/validator_real_frames.csv"
    rows = list(csv.DictReader(table.open()))
    counts = Counter((r["preset"], r["verdict"]) for r in rows)
    total = Counter(r["verdict"] for r in rows)
    assert len(rows) == 183 and total == {"PASS":128, "UNKNOWN":55}, total
    targets = [("barnards_star", "Barnard's Star"), ("epsilon_indi_b", "Epsilon Indi B"),
               ("wise_0855", "WISE 0855 field"), ("rw_aurigae", "RW Aurigae"), ("r_draconis", "R Draconis")]
    chart = r"""\begin{tikzpicture}
\begin{axis}[xbar stacked,width=.90\linewidth,height=5.1cm,
 xmin=0,xmax=46,ymin=-.6,ymax=4.6,bar width=13pt,
 ytick={0,1,2,3,4},yticklabels={R Draconis,RW Aurigae,WISE 0855 field,Epsilon Indi B,Barnard's Star},
 axis lines*=left,xlabel={Unique cutouts},xtick={0,10,20,30,40},
 tick label style={font=\small},label style={font=\small},
 xmajorgrids=true,grid style={gray!18},
 legend style={draw=none,font=\small,at={(.5,1.04)},anchor=south,legend columns=2},
 nodes near coords,point meta=explicit symbolic,nodes near coords style={font=\footnotesize,color=black}]
"""
    for verdict, color in [("PASS", "reportblue!48"), ("UNKNOWN", "gray!22")]:
        coords = " ".join(f"({counts[(key,verdict)]},{4-i})[{counts[(key,verdict)] or ''}]" for i,(key,_) in enumerate(targets))
        chart += r"\addplot[fill=" + color + r",draw=white] coordinates {" + coords + "};\n"
    chart += r"\legend{PASS,UNKNOWN}" + "\n" + r"\end{axis}\end{tikzpicture}" + "\n"
    (GENERATED / "registration-chart.tex").write_text(chart)

    # Scientific figure crops: preserve source values, fixed bounds, nearest-neighbor enlargement.
    # Both rows use the identical sky-grid crop; the second adds the existing adverse-flag layer.
    base = ROOT / "backend/content/presets/wise_0855/case-wise_0855_quality_trap"
    sources = []
    bounds = (86, 52, 150, 116)
    for label, key in [("A", "2025W45_2A_0278_1_D2"), ("B", "2025W46_1A_0108_1_D2")]:
        raw = base / (key + ".png")
        flag = base / (key + ".flags.png")
        image = Image.open(raw).convert("RGBA")
        mask = Image.open(flag).convert("RGBA")
        for suffix, pixels in [("sky", image), ("flags", Image.alpha_composite(image,mask))]:
            crop = pixels.crop(bounds)
            bg = Image.new("RGBA", crop.size, "black")
            bg.alpha_composite(crop)
            bg.convert("RGB").resize((512,512),Image.Resampling.NEAREST).save(GENERATED / f"wise-{label}-{suffix}.png")
        sources.append({"frame":key,"png":str(raw.relative_to(ROOT)),"sha256":sha(raw),"flag_sha256":sha(flag)})
    (GENERATED / "figure-data.json").write_text(json.dumps({"registration_source":str(table.relative_to(ROOT)),"registration_source_sha256":sha(table),"counts":dict(total),"wise_crop_xyxy":bounds,"wise_sources":sources,"resampling":"nearest; source pixel values retained; existing flag overlay only"},indent=2)+"\n")

def build(output, compiler):
    figures()
    BUILD.mkdir(exist_ok=True)
    command = [compiler, "--keep-logs", "--keep-intermediates", "--outdir", str(BUILD), str(SOURCE)]
    result = subprocess.run(command,cwd=HERE,capture_output=True,text=True)
    (BUILD / "compiler-output.txt").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-5000:])
    log = (BUILD / "perigee-report.log").read_text(errors="replace")
    bad = re.findall(r"(?:Overfull \\[hv]box[^\n]*|LaTeX Warning: (?:Reference|Citation)[^\n]*undefined[^\n]*|Missing character[^\n]*)",log)
    if bad:
        raise RuntimeError("Layout/reference errors: " + repr(bad))
    pdf = BUILD / "perigee-report.pdf"
    reader = PdfReader(pdf)
    texts = [p.extract_text() or "" for p in reader.pages]
    text = "\n".join(texts)
    flat = re.sub(r"\s+", " ", text)
    for name in NAMES:
        assert name in flat, name
    for fact in ["183", "189", "128", "55", "7.29", "10.25", "5.36", "5.38"]:
        assert fact in text, fact
    assert "??" not in text
    assert all(len(t)>100 for t in texts)
    assert 7 <= len(reader.pages) <= 12, len(reader.pages)
    output.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(pdf,output)
    (BUILD / "extracted.txt").write_text(text)
    verification = {"pages":len(reader.pages),"pdf_bytes":output.stat().st_size,"pdf_sha256":sha(output),
        "source_sha256":sha(SOURCE),"compiler":subprocess.check_output([compiler,"--version"],text=True).strip(),
        "typeface":"TeX Gyre Pagella / New PX", "selectable_text":True,"all_six_names_present":True,
        "unresolved_references":False,"overfull_boxes":False,"new_science_experiments_run":False,
        "verified_team_names":NAMES,"visual_review":"Pending final rendered-page inspection"}
    (HERE / "verification.json").write_text(json.dumps(verification,indent=2)+"\n")
    print(json.dumps(verification,indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT / "frontend/public/demo/perigee-technical-report.pdf")
    parser.add_argument("--compiler",default=shutil.which("tectonic") or str(Path.home()/".local/bin/tectonic"))
    args=parser.parse_args()
    build(args.output.resolve(),args.compiler)
