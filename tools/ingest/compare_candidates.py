"""Run another processor candidate and this branch on the same 183 original files and compare.

    git -C . archive origin/codex/parallel-05-processor-a backend/data | tar x -C /tmp/procA
    python tools/ingest/compare_candidates.py --other /tmp/procA/backend/data/process.py --raw ../perigee-data/raw [--fov 6]

Expects the other module to expose processor-a's API (process_frame, FrameInput, TargetInput).
Compares quality status and pixel counts, wavelength, marker position, time, image
registration (field cross-correlation between the two PNGs), coverage, speed and PNG size.
"""
import argparse, sys, json, time, io, math, importlib.util
from pathlib import Path
import numpy as np
from PIL import Image
REPO = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(); ap.add_argument('--other', required=True); ap.add_argument('--raw', required=True, type=Path)
ap.add_argument('--fov', type=float, default=6.0); ap.add_argument('--out', type=Path)
args = ap.parse_args()
sys.path.insert(0, str(REPO / 'backend')); sys.path.insert(0, str(REPO / 'tools' / 'ingest'))
import data
from data import CatalogTarget, FrameContext, ObservationDescriptor, process_frame
from check_registration import field_shift
spec = importlib.util.spec_from_file_location('procA', args.other)
A = importlib.util.module_from_spec(spec); sys.modules['procA'] = A; spec.loader.exec_module(A)

m = json.load(open(REPO / 'research/build_data/manifest.json'))
T = {t['id']: t for t in m['targets']}
files = [f for f in m['files'] if f['status'] == 'downloaded']
FOV = args.fov
rows = []; ta = tb = 0.0
for f in files:
    t = T[f['target_id']]
    b = (args.raw / f['target_id'] / Path(f['file']).name).read_bytes()
    tinA = A.TargetInput(t['ra_j2000_deg'], t['dec_j2000_deg'], t['reference_epoch_jyear'], t['pm_ra_cosdec_masyr'], t['pm_dec_masyr'], t.get('parallax_mas'), t.get('radial_velocity_kms'), t['name'], 'SIMBAD')
    t0 = time.time()
    pa = A.process_frame(b, A.FrameInput(t['query_ra_deg'], t['query_dec_deg'], FOV, 256, tinA, f['archive_url'], f['obs_id'], f['collection'], f['detector']))
    ta += time.time() - t0
    tgt = CatalogTarget(f['target_id'], t['name'], t['ra_j2000_deg'], t['dec_j2000_deg'], t['reference_epoch_jyear'], t['pm_ra_cosdec_masyr'], t['pm_dec_masyr'], 'SIMBAD', t.get('parallax_mas'), t.get('radial_velocity_kms'))
    t0 = time.time()
    pb = process_frame(b, FrameContext(ObservationDescriptor(f['obs_id'], f['collection'], None, None, f['detector'], f['archive_url']), t['query_ra_deg'], t['query_dec_deg'], FOV, 256, tgt))
    tb += time.time() - t0
    ra, rb = pa.record, pb.record
    def img(png):
        a = np.asarray(Image.open(io.BytesIO(png)).convert('LA'), float)
        v = a[..., 0]; v[a[..., 1] == 0] = np.nan; return v
    row = {
        'key': rb['frame_key'], 'keyA': ra['frame_key'],
        'statusA': ra['quality']['status'], 'statusB': rb['quality']['status'],
        'advA': ra['quality']['adverse_aperture_pixels'], 'advB': rb['quality']['adverse_aperture_pixels'],
        'validA': ra['quality']['valid_aperture_pixels'], 'validB': rb['quality']['valid_aperture_pixels'],
        'wlA': ra['wavelength_um'], 'wlB': rb['wavelength_um'],
        'mjdA': ra['mjd'], 'mjdB': rb['mjd'],
        'mA': None if not ra['marker'] else (ra['marker']['x'], ra['marker']['y']),
        'mB': None if not rb['marker'] else (rb['marker']['x'], rb['marker']['y']),
        'pngA': len(pa.png_bytes) + len(pa.flag_png_bytes or b''), 'pngB': len(pb.image_png) + len(pb.flag_png or b''),
        'coverA': float(np.isfinite(img(pa.png_bytes)).mean()), 'coverB': float(np.isfinite(img(pb.image_png)).mean()),
    }
    if f['target_id'] in ('epsilon_indi_b', 'barnards_star') and len(rows) % 4 == 0:
        ia, ib = img(pa.png_bytes), img(pb.image_png)
        yy, xx = np.mgrid[0:256, 0:256]
        dx, dy, _ = field_shift(ia, ib, (xx - 128) ** 2 + (yy - 128) ** 2 > 30 ** 2)
        row['img_shift_px'] = (round(dx, 2), round(dy, 2))
    rows.append(row)
if args.out: args.out.write_text(json.dumps(rows, indent=0))
n = len(rows)
st = [r for r in rows if r['statusA'] != r['statusB']]
adv = [r for r in rows if r['statusA'] == r['statusB'] and r['advA'] != r['advB']]
val = [r for r in rows if r['statusA'] == r['statusB'] and r['validA'] != r['validB']]
wl = [abs(r['wlA'] - r['wlB']) for r in rows if r['wlA'] is not None and r['wlB'] is not None]
wln = [r['key'] for r in rows if (r['wlA'] is None) != (r['wlB'] is None)]
mk = [math.hypot(r['mA'][0] - r['mB'][0], r['mA'][1] - r['mB'][1]) for r in rows if r['mA'] and r['mB']]
tm = [abs(r['mjdA'] - r['mjdB']) * 86400 for r in rows]
sh = [r['img_shift_px'] for r in rows if 'img_shift_px' in r]
print(f'fov {FOV}: {n} frames; keys equal: {all(r["key"] == r["keyA"] for r in rows)}')
print(f'status differs: {len(st)}; adverse-count differs: {len(adv)}; valid-count differs: {len(val)}')
for r in st[:10]: print('  status', r['key'], r['statusA'], '->', r['statusB'], r['validB'], r['advB'])
print(f'wavelength max |A-B|: {max(wl):.2e} um; null mismatch: {wln}')
print(f'marker max |A-B|: {max(mk):.3f} display px; time max |A-B|: {max(tm):.4f} s')
print(f'image field shift A vs B on {len(sh)} sampled frames: {sh}')
print(f'mean grid coverage: A {np.mean([r["coverA"] for r in rows]):.3f}  B {np.mean([r["coverB"] for r in rows]):.3f}')
print(f'process time per frame: A {ta / n * 1000:.0f} ms  B {tb / n * 1000:.0f} ms; PNG bytes per frame (image+flags): A {np.mean([r["pngA"] for r in rows]):.0f}  B {np.mean([r["pngB"] for r in rows]):.0f}')
