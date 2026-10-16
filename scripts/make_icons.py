#!/usr/bin/env python3
"""Generate favicon.svg, favicon.ico and apple-touch-icon.png (gold sun mark). Run once; outputs are committed."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "icons"
GOLD = (215, 154, 30, 255)
INK = (27, 33, 80, 255)
OUT.mkdir(parents=True, exist_ok=True)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<circle cx="32" cy="32" r="11" fill="#D79A1E"/>
<g stroke="#D79A1E" stroke-width="3.4" stroke-linecap="round">
      <path d="M32.0 13.0L32.0 3.0 M45.4 18.6L52.5 11.5 M51.0 32.0L61.0 32.0 M45.4 45.4L52.5 52.5 M32.0 51.0L32.0 61.0 M18.6 45.4L11.5 52.5 M13.0 32.0L3.0 32.0 M18.6 18.6L11.5 11.5"/>
      <path stroke-width="2.6" d="M39.7 13.5L42.1 7.5 M50.5 24.3L56.5 21.9 M50.5 39.7L56.5 42.1 M39.7 50.5L42.1 56.5 M24.3 50.5L21.9 56.5 M13.5 39.7L7.5 42.1 M13.5 24.3L7.5 21.9 M24.3 13.5L21.9 7.5"/>
    </g></svg>
"""
(OUT / "favicon.svg").write_text(SVG)

def sun(size, bg=None, scale=1.0, big=True):
    S = size * 4
    im = Image.new("RGBA", (S, S), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    u = S / 64 * scale
    r = 11 * u
    d.ellipse([c - r, c - r, c + r, c + r], fill=GOLD)
    for i in range(16):
        a = math.radians(i * 22.5)
        long = i % 2 == 0
        r0, r1 = (19 * u, 29 * u) if long else (20 * u, 26.5 * u)
        w = (3.4 if long else 2.6) * u
        x0, y0, x1, y1 = c + r0 * math.sin(a), c - r0 * math.cos(a), c + r1 * math.sin(a), c - r1 * math.cos(a)
        d.line([x0, y0, x1, y1], fill=GOLD, width=round(w))
        for x, y in ((x0, y0), (x1, y1)):
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=GOLD)
    return im.resize((size, size), Image.LANCZOS)

sun(180, bg=INK, scale=.82).convert("RGB").save(OUT / "apple-touch-icon.png")
big = sun(256)
big.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("icons written")
