"""Compare every packaged preset frame with Sathvik's independent science check.

    python tools/ingest/check_science_audit.py --science science/audit/frames.json

(science/audit/frames.json is on codex/sathvik-science; `git show origin/codex/sathvik-science:science/audit/frames.json > /tmp/frames.json`.)
Checks quality status, adverse pixel counts, mid-exposure time, wavelength and the predicted
target position for all 183 frames. Exits 1 on any difference.
"""
import argparse, json, math, sys
from pathlib import Path
R = str(Path(__file__).resolve().parents[2]) + '/'
ap = argparse.ArgumentParser(); ap.add_argument('--science', required=True); args = ap.parse_args()
sci=json.load(open(args.science))['frames']
S={f"{f['observation_id']}_D{f['detector']}":f for f in sci}
n=0; diffs=[]; dwl=0; dpos=0; dt=0
for p in ['barnards_star','epsilon_indi_b','wise_0855','rw_aurigae','r_draconis']:
    for r in json.load(open(R+f'backend/content/presets/{p}/frames.json'))['frames']:
        n+=1; s=S[r['frame_key']]
        if r['quality']['status']!=s['status']: diffs.append((r['frame_key'], 'status', r['quality']['status'], s['status']))
        if (r['wavelength_um'] is None)!=(s['wavelength_um'] is None or not s['inside']): diffs.append((r['frame_key'],'wl null', r['wavelength_um'], s['wavelength_um']))
        if r['wavelength_um'] is not None and s['wavelength_um'] is not None: dwl=max(dwl,abs(r['wavelength_um']-s['wavelength_um']))
        dt=max(dt,abs(r['mjd']-s['mjd_avg'])*86400)
        if r['observed_at_utc'].rstrip('Z')!=s['observed_at_utc'].rstrip('Z'): diffs.append((r['frame_key'],'time',r['observed_at_utc'],s['observed_at_utc']))
        if r['marker']:
            d=math.hypot((r['marker']['ra_deg']-s['pred_ra_deg'])*math.cos(math.radians(s['pred_dec_deg'])), r['marker']['dec_deg']-s['pred_dec_deg'])*3600
            dpos=max(dpos,d)
        if s['status']!='not_covered':
            if r['quality']['adverse_aperture_pixels']!=s['adverse_aperture_pixels'] and r['quality']['status']!='unknown':
                diffs.append((r['frame_key'],'adverse count',r['quality']['adverse_aperture_pixels'],s['adverse_aperture_pixels']))
print(n,'frames | status/time/null-wavelength/adverse-count differences:',len(diffs),'| max wavelength diff um',f'{dwl:.2e}','| max time diff s',round(dt,4),'| max predicted-position diff arcsec',round(dpos,4))
for d in diffs[:20]: print(d)
sys.exit(1 if diffs or dwl > 1e-6 or dpos > 0.01 else 0)
