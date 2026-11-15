"""N6 / D1 bounded corruption sweep (run from the repo root with PERIGEE_DATA_ROOT set): zero (or 0xFF-fill) one 2880-byte block of a retained cutout at a
time and run process_frame. Children restart after any hard crash so every block is tried.
Prints a summary of outcome classes per HDU."""
import subprocess, sys, json, collections
from pathlib import Path

import os
RAW = os.path.join(os.environ["PERIGEE_DATA_ROOT"], "raw/epsilon_indi_b/level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits")
CHILD = r'''
import sys, json; sys.path.insert(0, ".")
from backend.data.process import FrameInput, process_frame
raw = open(sys.argv[1], "rb").read()
fill = bytes([int(sys.argv[2])]) * 2880
blocks = [int(b) for b in sys.argv[3].split(",")]
fi = FrameInput(query_ra_deg=331.0966687831005, query_dec_deg=-56.80064917516836)
for b in blocks:
    print("START", b, flush=True)
    data = raw[: b * 2880] + fill + raw[(b + 1) * 2880 :]
    try:
        out = process_frame(data, fi)
        print("RES", b, "ok", out.record["quality"]["status"], out.record["wavelength_um"] is not None, flush=True)
    except Exception as e:
        print("RES", b, "exc", type(e).__name__, flush=True)
'''
raw_len = Path(RAW).stat().st_size
nblocks = raw_len // 2880
# All non-EPSF blocks plus every 50th EPSF block.
candidates = [b for b in range(nblocks) if b < 45 or b >= nblocks - 3 or b % 50 == 0]
results = {}
for fill in (0, 255):
    todo = list(candidates)
    while todo:
        r = subprocess.run([sys.executable, "-c", CHILD, RAW, str(fill), ",".join(map(str, todo))], capture_output=True, text=True)
        done = set()
        last = None
        for line in r.stdout.splitlines():
            p = line.split()
            if p[0] == "START":
                last = int(p[1])
            elif p[0] == "RES":
                results[(fill, int(p[1]))] = " ".join(p[2:])
                done.add(int(p[1]))
        if r.returncode != 0 and last is not None and last not in done:
            results[(fill, last)] = f"CRASH rc={r.returncode}"
            done.add(last)
        todo = [b for b in todo if b not in done]
        if r.returncode == 0:
            break
hdus = [("PRIMARY", 0, 1), ("IMAGE", 1, 14), ("FLAGS", 14, 25), ("VARIANCE", 25, 34), ("ZODI", 34, 43), ("EPSF", 43, 1416), ("WCS-WAVE", 1416, 1418)]
def hdu_of(b):
    return next(n for n, a, z in hdus if a <= b < z)
summary = collections.Counter((fill, hdu_of(b), v.split()[0] + (" " + v.split()[1] if v.startswith(("exc", "CRASH")) else "")) for (fill, b), v in results.items())
for k in sorted(summary):
    print(k, summary[k])
print("crashes:", sorted(k for k, v in results.items() if v.startswith("CRASH")))
print("ok-with-status:", collections.Counter(v for v in results.values() if v.startswith("ok")))
