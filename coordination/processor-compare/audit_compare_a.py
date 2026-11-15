"""Sagar's check_science_audit.py comparison, applied to processor A's preset records.

Usage: .venv/bin/python coordination/processor-compare/audit_compare_a.py <science/audit/frames.json from origin/codex/sathvik-science>
"""
import json
import math
import sys

sci = {f"{f['observation_id']}_D{f['detector']}": f for f in json.load(open(sys.argv[1]))["frames"]}
n, diffs, dwl, dpos, dt = 0, [], 0.0, 0.0, 0.0
for p in ["barnards_star", "epsilon_indi_b", "wise_0855", "rw_aurigae", "r_draconis"]:
    for r in json.load(open(f"backend/content/presets/{p}/frames/frames.json"))["frames"]:
        n += 1
        s = sci[r["frame_key"]]
        if r["quality"]["status"] != s["status"]:
            diffs.append((r["frame_key"], "status"))
        if (r["wavelength_um"] is None) != (s["wavelength_um"] is None or not s["inside"]):
            diffs.append((r["frame_key"], "wl null"))
        if r["wavelength_um"] is not None and s["wavelength_um"] is not None:
            dwl = max(dwl, abs(r["wavelength_um"] - s["wavelength_um"]))
        dt = max(dt, abs(r["mjd"] - s["mjd_avg"]) * 86400)
        if r["observed_at_utc"].rstrip("Z") != s["observed_at_utc"].rstrip("Z"):
            diffs.append((r["frame_key"], "time"))
        if r["marker"]:
            dpos = max(dpos, math.hypot((r["marker"]["ra_deg"] - s["pred_ra_deg"]) * math.cos(math.radians(s["pred_dec_deg"])),
                                        r["marker"]["dec_deg"] - s["pred_dec_deg"]) * 3600)
        if s["status"] != "not_covered" and r["quality"]["adverse_aperture_pixels"] != s["adverse_aperture_pixels"]:
            diffs.append((r["frame_key"], "adverse count"))
print(n, "frames | differences:", len(diffs), "| max wavelength diff um", f"{dwl:.2e}", "| max time diff s", round(dt, 4),
      "| max predicted-position diff arcsec", round(dpos, 4), diffs[:10])
