"""Time a full processor-A product build (5 presets + 2 cases) into an empty --out dir.

Usage (from a checkout of the integration branch):
    .venv/bin/python coordination/processor-compare/time_build_a.py --data-root <build_data> --out <empty dir>
"""
import argparse
import subprocess
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--data-root", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
jobs = [["preset", p] for p in ("barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis")]
jobs += [["case", c] for c in ("fair_comparison", "moving_neighbor")]
t0 = time.monotonic()
for kind, ident in jobs:
    r = subprocess.run([sys.executable, "-m", "tools.ingest.ingest", kind, ident, "--data-root", a.data_root, "--out", a.out],
                       capture_output=True, text=True)
    print(kind, ident, "exit", r.returncode, r.stderr.strip()[-300:] if r.returncode else "")
print(f"total_s {time.monotonic() - t0:.2f}")
