"""Render the 1200 × 630 share card using the bundled, licensed brand font.

Run from any directory:
  uv run --with pillow --with fonttools --with brotli python coordination/generate-social-preview.py

This is a typographic graphic, not a NASA observation or simulated scientific image.
No external images, fonts, network calls, or image-generation model are used.
"""

from io import BytesIO
from math import cos, pi, sin
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


ROOT = Path(__file__).resolve().parents[1]
SCALE = 3
SIZE = (1200, 630)
BLACK = "#08090a"
WHITE = "#f5f6f7"
CITRON = "#d5f96e"
MUTED = "#b3b7bd"


def font(size: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    face = TTFont(ROOT / "frontend/public/fonts/host-grotesk-latin.woff2")
    if "fvar" in face:
        face = instantiateVariableFont(face, {"wght": weight}, inplace=True)
    face.flavor = None
    data = BytesIO()
    face.save(data)
    data.seek(0)
    return ImageFont.truetype(data, size * SCALE)


image = Image.new("RGB", (SIZE[0] * SCALE, SIZE[1] * SCALE), BLACK)
draw = ImageDraw.Draw(image)


def text(x: int, y: int, content: str, size: int, color: str, weight: int = 500):
    draw.text((x * SCALE, y * SCALE), content, font=font(size, weight), fill=color, anchor="lt")


def ellipse(cx: float, cy: float, rx: float, ry: float, rotation: float, color: str, width: float):
    angle = rotation * pi / 180
    # Filled contours keep thick, rotated curves smooth at social-preview scale.
    for offset, fill in ((width / 2, color), (-width / 2, BLACK)):
        points = []
        for step in range(720):
            theta = step * pi / 360
            x, y = (rx + offset) * cos(theta), (ry + offset) * sin(theta)
            points.append(((cx + x * cos(angle) - y * sin(angle)) * SCALE,
                           (cy + x * sin(angle) + y * cos(angle)) * SCALE))
        draw.polygon(points, fill=fill)


def brand_mark(cx: int, cy: int, scale: float, color: str, point: str):
    ellipse(cx, cy, 18 * scale, 10 * scale, -34, color, 1.6 * scale)
    ellipse(cx, cy, 7 * scale, 7 * scale, 0, color, 1.6 * scale)
    px, py, r = cx + 13.5 * scale, cy - 9.2 * scale, 3.1 * scale
    draw.ellipse(((px-r)*SCALE, (py-r)*SCALE, (px+r)*SCALE, (py+r)*SCALE), fill=point)


# The large mark is decorative brand geometry, never a plotted orbit or data.
brand_mark(1005, 280, 9.4, "#30372b", CITRON)
brand_mark(94, 88, 1.3, WHITE, CITRON)
text(133, 69, "perigee", 38, WHITE, 600)

text(72, 192, "Investigate NASA’s", 73, WHITE)
text(72, 278, "infrared sky", 82, CITRON)
text(76, 397, "Compare SPHEREx observations.", 28, MUTED, 400)
text(76, 438, "Record what the evidence supports.", 28, MUTED, 400)

draw.line((76*SCALE, 533*SCALE, 1124*SCALE, 533*SCALE), fill="#303438", width=SCALE)
text(76, 558, "Notice  /  Check  /  Record", 21, WHITE)
metadata = PngImagePlugin.PngInfo()
metadata.add_text("Title", "Perigee · Investigate NASA's infrared sky")
metadata.add_text("Description", "Compare real NASA SPHEREx observations and record what the evidence supports.")
metadata.add_text("Source", "Perigee brand mark; bundled Host Grotesk font (SIL Open Font License). No scientific imagery.")
metadata.add_text("AI assistance", "OpenAI Codex assisted the layout and rendering code. No image-generation model was used.")
output = ROOT / "frontend/public/social-preview.png"
image.resize(SIZE, Image.Resampling.LANCZOS).save(output, pnginfo=metadata, optimize=True)
print(f"Wrote {output}: {SIZE[0]} × {SIZE[1]}, {output.stat().st_size:,} bytes")
