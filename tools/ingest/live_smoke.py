"""Live smoke test against the real IRSA archive (bounded: 1 search + up to 3 frames per position).

    python tools/ingest/live_smoke.py [--out tools/ingest/evidence/live_smoke.json]

Positions:
  m13             RA 250.4235, Dec 36.4613 - globular cluster M13. Not a preset; chosen because it
                  is well covered by the SPHEREx wide survey (149 QR3 records found on 2026-11-14)
                  and full of stars, so a bad registration or blank frame would be obvious.
  wise_0855_official  RA 08h55m10.831s, Dec -07d14m42.53s - the official challenge coordinate,
                  tested separately from the proper-motion-predicted position used by the preset.
Run it when it can answer a real integration question, not on every change.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from data import DataError, SearchQuery, fetch_and_process, search_observations  # noqa: E402

POSITIONS = {
    "m13": (250.4235, 36.4613),
    "wise_0855_official": (133.79512916666667, -7.245147222222222),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "tools" / "ingest" / "evidence" / "live_smoke.json")
    ap.add_argument("--frames", type=int, default=3)
    args = ap.parse_args()
    report = {"run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "positions": {}}
    for name, (ra, dec) in POSITIONS.items():
        entry: dict = {"ra_deg": ra, "dec_deg": dec}
        q = SearchQuery.validated(ra, dec, 6, 12)
        t0 = time.time()
        try:
            res = search_observations(q)
        except DataError as exc:
            entry["search"] = {"error": exc.to_dict(), "seconds": round(time.time() - t0, 2)}
            report["positions"][name] = entry
            print(name, "search error", exc.to_dict())
            continue
        d = res.to_dict()
        entry["search"] = {
            "seconds": round(time.time() - t0, 2),
            **{k: d[k] for k in ("status", "returned_count", "total_matches", "truncated", "warnings", "collections_queried")},
            "first": d["observations"][0] if d["observations"] else None,
        }
        print(name, "search", entry["search"]["status"], d["returned_count"], "of", d["total_matches"], f"{entry['search']['seconds']}s")
        picks = res.observations
        if picks:
            idx = sorted({0, len(picks) // 2, len(picks) - 1})[: args.frames]
            entry["frames"] = []
            for i in idx:
                o = picks[i]
                t1 = time.time()
                try:
                    p = fetch_and_process(o, q.ra_deg, q.dec_deg, q.fov_arcmin)
                    rec = p.with_data_urls()
                    f = {
                        "observation_id": o.observation_id,
                        "seconds": round(time.time() - t1, 2),
                        "response_json_bytes": len(json.dumps(rec)),
                        "observed_at_utc": rec["observed_at_utc"],
                        "wavelength_um": rec["wavelength_um"],
                        "quality": rec["quality"]["status"],
                        "cutout_url": rec["provenance"]["cutout_url"],
                        "sha256": rec["provenance"]["sha256"],
                    }
                except DataError as exc:
                    f = {"observation_id": o.observation_id, "seconds": round(time.time() - t1, 2), "error": exc.to_dict()}
                entry["frames"].append(f)
                print("   frame", f)
        report["positions"][name] = entry
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
