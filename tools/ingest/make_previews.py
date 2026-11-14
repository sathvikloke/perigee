"""Review images for the candidate comparison sets (for Sathvik's scientific check).

    python tools/ingest/make_previews.py

Reads the packaged assets in backend/content/presets and writes, for each set,
tools/ingest/evidence/<set_id>.png (frames side by side: image + hatched adverse flags +
cyan circle at the catalog-predicted position, transparent no-data shown dark green) and
tools/ingest/evidence/<set_id>.gif (blink, no flag overlay). Review aids only; the app renders
the same PNG assets itself.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
PRESETS = REPO / "backend" / "content" / "presets"
OUT = REPO / "tools" / "ingest" / "evidence"
SCALE = 2


def compose(assets: dict, rec: dict, with_flags: bool) -> Image.Image:
    img = Image.open(PRESETS / assets[rec["image"]["asset_id"]]["path"]).convert("RGBA")
    base = Image.new("RGBA", img.size, (30, 60, 30, 255))
    base.alpha_composite(img)
    if with_flags and rec.get("flag_image"):
        base.alpha_composite(Image.open(PRESETS / assets[rec["flag_image"]["asset_id"]]["path"]).convert("RGBA"))
    base = base.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(base)
    if rec.get("marker"):
        x, y = rec["marker"]["x"] * SCALE, rec["marker"]["y"] * SCALE
        d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(0, 200, 255, 255), width=2)
    wl = rec["wavelength_um"]
    label = f"{rec['observed_at_utc'][:10]}  D{rec['detector']}  {'?' if wl is None else f'{wl:.4f}'} um  {rec['quality']['status']}"
    d.rectangle([0, 0, base.width, 18], fill=(0, 0, 0, 200))
    d.text((6, 4), label, fill=(255, 255, 0, 255))
    return base


def main() -> int:
    index = json.loads((PRESETS / "manifest.json").read_text())
    assets = index["assets"]
    OUT.mkdir(parents=True, exist_ok=True)
    for p in index["presets"]:
        for s in p["comparison_sets"]:
            doc = json.loads((PRESETS / s["path"]).read_text())
            tiles = [compose(assets, r, True) for r in doc["frames"]]
            w, h = tiles[0].size
            sheet = Image.new("RGBA", (len(tiles) * (w + 8) - 8, h), (0, 0, 0, 255))
            for i, t in enumerate(tiles):
                sheet.paste(t, (i * (w + 8), 0))
            sheet.convert("RGB").save(OUT / f"{s['set_id']}.png", optimize=True)
            frames = [compose(assets, r, False).convert("RGB") for r in doc["frames"]]
            frames[0].save(OUT / f"{s['set_id']}.gif", save_all=True, append_images=frames[1:], duration=800, loop=0)
            print(s["set_id"], (OUT / f"{s['set_id']}.png").stat().st_size, (OUT / f"{s['set_id']}.gif").stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
