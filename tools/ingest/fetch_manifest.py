"""Re-download the audited SPHEREx cutouts listed in research/build_data/manifest.json
and check each file against the SHA-256 recorded during the original audit.

Usage:
    python tools/ingest/fetch_manifest.py --out ../perigee-data/raw [--target epsilon_indi_b] [--workers 3]

Files land in <out>/<target_id>/<filename>. Existing files whose hash already matches are
skipped. The data directory should live outside the repository (raw FITS are git-ignored).
A hash mismatch is reported, not hidden: it means IRSA served different bytes than the audit saw.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "research" / "build_data" / "manifest.json"
ALLOWED_PREFIX = "https://irsa.ipac.caltech.edu/ibe/data/spherex/"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(entry: dict, out: Path, attempts: int = 3) -> dict:
    url = entry["source_url"]
    if not url.startswith(ALLOWED_PREFIX):
        return {"file": entry["file"], "result": "refused_url"}
    dest = out / entry["target_id"] / Path(entry["file"]).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha256(dest) == entry["sha256"]:
        return {"file": entry["file"], "result": "already_verified"}
    last_err = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "perigee-ingest/0.1"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if not data.startswith(b"SIMPLE  ="):
                raise ValueError("response is not a FITS file")
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            got = sha256(dest)
            return {
                "file": entry["file"],
                "result": "verified" if got == entry["sha256"] else "hash_mismatch",
                "sha256": got,
            }
        except Exception as exc:  # bounded retries, then report
            last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (i + 1))
    return {"file": entry["file"], "result": "failed", "error": last_err}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--target", action="append")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    entries = [e for e in manifest["files"] if e["status"] == "downloaded"]
    if args.target:
        entries = [e for e in entries if e["target_id"] in args.target]
    results = []
    with cf.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as pool:
        for r in pool.map(lambda e: fetch(e, args.out), entries):
            results.append(r)
            print(r["result"], r["file"], r.get("error", ""), flush=True)
    summary: dict[str, int] = {}
    for r in results:
        summary[r["result"]] = summary.get(r["result"], 0) + 1
    print(json.dumps(summary))
    (args.out / "fetch_report.json").write_text(json.dumps({"summary": summary, "results": results}, indent=1))
    return 0 if set(summary) <= {"verified", "already_verified"} else 1


if __name__ == "__main__":
    sys.exit(main())
