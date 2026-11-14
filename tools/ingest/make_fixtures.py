"""Make the small test fixtures in backend/tests/data/fixtures/ from retained original data.

    python tools/ingest/make_fixtures.py --raw ../perigee-data/raw --sia ../perigee-data/sia_qr3_barnard.xml

Fixtures (each listed in fixtures/README.md with its source):
  *.fits.fixture   real SPHEREx Level 2 cutouts with the EPSF and ZODI extensions removed
                   (~50 KB instead of ~4 MB). Pixel, flag, variance and wavelength-table data
                   are untouched. The extension is not ".fits" because *.fits is git-ignored.
  sia_qr3_barnard_trimmed.xml   a real IRSA SIA v2 response cut down to its first 6 rows.
"""
from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

from astropy.io import fits

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "backend" / "tests" / "data" / "fixtures"
FILES = {
    "epsindb_2026W18_1A_0516_1D3.fits.fixture": ("epsilon_indi_b", "level2_2026W18_1A_0516_1D3_spx_l2b-v27-2026-244.fits"),
    "barnard_2025W34_2B_0557_4D2.fits.fixture": ("barnards_star", "level2_2025W34_2B_0557_4D2_spx_l2b-v27-2026-229.fits"),
}


def trim(path: Path) -> bytes:
    with fits.open(path) as hdul:
        keep = fits.HDUList([h.copy() for h in hdul if h.name in ("PRIMARY", "IMAGE", "FLAGS", "VARIANCE", "WCS-WAVE")])
        buf = io.BytesIO()
        keep.writeto(buf)
        return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--sia", type=Path)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (tid, fn) in FILES.items():
        matches = list((args.raw / tid).glob(fn.replace("2026-229", "*")))
        src = args.raw / tid / fn if (args.raw / tid / fn).exists() else matches[0]
        (OUT / name).write_bytes(trim(src))
        print(name, (OUT / name).stat().st_size)
    if args.sia:
        text = args.sia.read_text()
        rows = re.findall(r"<TR>.*?</TR>", text, flags=re.S)
        head, tail = text.split("<TR>", 1)[0], text.rsplit("</TR>", 1)[1]
        (OUT / "sia_qr3_barnard_trimmed.xml").write_text(head + "".join(rows[:6]) + tail)
        print("sia rows kept", min(6, len(rows)), "of", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
