"""Compare an exported evidence card with the API's FrameRecords, field by field."""
import json, sys

card = json.load(open(sys.argv[1]))
api = {}
for path in sys.argv[2:]:
    for f in json.load(open(path))["frames"]:
        api.setdefault(f["frame_key"], f)

checks = 0
bad = []
for e in card["frames"]:
    f = api[e["frame_key"]]
    pairs = {
        "frame_id": f["frame_id"],
        "observation_id": f["observation_id"],
        "detector": f["detector"],
        "collection_id": f["collection_id"],
        "observed_at_utc": f["observed_at_utc"],
        "mjd": f["mjd"],
        "wavelength_um": f["wavelength_um"],
        "bandwidth_um": f["bandwidth_um"],
        "wavelength_location": f["wavelength_location"],
        "quality_status": f["quality"]["status"],
        "quality_flag_names": f["quality"]["flag_names"],
        "display_scale_mode": f["display_scale"]["mode"],
        "source_url": f["source_url"],
    }
    proc = {
        "processing_version": f["provenance"]["processing_version"],
        "file_sha256": f["provenance"].get("file_sha256") or f["provenance"].get("sha256"),
        "pipeline_version": f["provenance"].get("pipeline_version"),
        "registration_method": f["registration"].get("method"),
        "display_scale_method": f["display_scale"].get("method"),
        "marker_kind": f["marker"]["kind"],
    }
    for k, v in pairs.items():
        checks += 1
        got = e[k]
        # The client normalizes UTC to ISO with Z; compare instants.
        if k == "observed_at_utc":
            ok = got.rstrip("Z").startswith(str(v).rstrip("Z")[:23]) or got.rstrip("Z")[:19] == str(v)[:19]
        else:
            ok = got == v
        if not ok:
            bad.append((e["frame_key"], k, got, v))
    for k, v in proc.items():
        checks += 1
        if e["processing"][k] != v:
            bad.append((e["frame_key"], "processing." + k, e["processing"][k], v))
    print(e["ref"], e["frame_key"], "api utc:", f["observed_at_utc"], "export utc:", e["observed_at_utc"])
print("field checks:", checks, "mismatches:", len(bad))
for b in bad:
    print("  MISMATCH", b)
for k in ("case_id", "preset_id", "query", "claim", "observations", "uncertainty", "app_version", "data_origin"):
    print(f"{k}: {card[k]!r}")
print("sources:", [s["url"] for s in card["sources"]])
blob = json.dumps(card)
print("contains image/asset data:", any(s in blob for s in ("data:image", "/api/v1/assets", "base64")))
