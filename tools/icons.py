#!/usr/bin/env python3
"""Draw the favicon, the touch icon and the social share image.

    python3 tools/icons.py

Original work, drawn here, with no dependency beyond the standard
library — zlib is all a PNG needs. Nothing is taken from an icon pack:
those archives are overwhelmingly unlicensed re-uploads, and a mark on a
client's site is the last place to find out.

PLACEHOLDERS. The graphiste authors the real logo and iconography; this
is what stands in the browser tab until she does, so that the tab is not
a blank page icon and a pasted link is not a grey rectangle. The mark is
deliberately generic — a point on a circle, a distance travelled — and
carries no letterform, because a letterform would be a logo and that is
hers to design.
"""

import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

# The palette, from site.css. Light ground, ink mark.
PAPER = (0xF4, 0xF5, 0xF7)
INK = (0x14, 0x17, 0x1C)


def png(path: Path, w: int, h: int, pixel) -> None:
    """Write an RGB PNG. `pixel(x, y)` returns an (r, g, b) tuple."""
    rows = bytearray()
    for y in range(h):
        rows.append(0)                       # filter type 0, none
        for x in range(w):
            rows.extend(pixel(x, y))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )


def mix(a, b, t: float):
    """Blend two colours. `t` is how much of `b`, clamped."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def coverage(d: float, edge: float) -> float:
    """Analytic anti-aliasing: how much of a pixel at signed distance `d`
    from an edge is inside it. One sample per pixel, no supersampling —
    a ring and a disc are both exactly expressible, so guessing with
    extra samples would be slower and no more correct."""
    return 0.5 - d / edge


def mark(w: int, h: int, scale: float):
    """A ring with a point on it. Returns a pixel function.

    `scale` is the ring's radius as a fraction of the shorter side, so
    the same drawing works at 180px and at 630px."""
    cx, cy = w / 2, h / 2
    short = min(w, h)
    r = short * scale
    stroke = max(1.0, short * scale * 0.14)
    dot = max(1.5, short * scale * 0.19)
    # The point sits at the top of the circle: a position on a path
    # rather than a decoration placed beside it.
    px, py = cx, cy - r
    aa = 1.2                                  # edge softness, in pixels

    def pixel(x: int, y: int):
        sx, sy = x + 0.5, y + 0.5
        out = PAPER

        d_ring = abs(((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5 - r) - stroke / 2
        out = mix(out, INK, coverage(d_ring, aa))

        d_dot = ((sx - px) ** 2 + (sy - py) ** 2) ** 0.5 - dot
        return mix(out, INK, coverage(d_dot, aa))

    return pixel


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <!-- Placeholder mark. The graphiste authors the real one. A point on a
       circle: a distance travelled, and no letterform, because a
       letterform would be a logo. -->
  <style>
    .ground { fill: #f4f5f7 }
    .mark   { fill: none; stroke: #14171c; stroke-width: 5 }
    .point  { fill: #14171c }
    /* An SVG favicon can answer the browser's theme, which a .ico
       cannot. In a dark tab strip the light ground would be a bright
       square; here it simply inverts. */
    @media (prefers-color-scheme: dark) {
      .ground { fill: #101317 }
      .mark   { stroke: #eef1f5 }
      .point  { fill: #eef1f5 }
    }
  </style>
  <rect class="ground" width="64" height="64" rx="12"/>
  <circle class="mark" cx="32" cy="34" r="17"/>
  <circle class="point" cx="32" cy="17" r="6"/>
</svg>
"""


def main() -> int:
    STATIC.mkdir(exist_ok=True)

    (STATIC / "favicon.svg").write_text(FAVICON, encoding="utf-8")

    # iOS ignores SVG favicons and has no dark variant for a touch icon,
    # so this one is light-ground only, which is what it is placed on.
    png(STATIC / "icon-180.png", 180, 180, mark(180, 180, 0.30))

    # 1200x630 is what the social cards expect. No text: we cannot
    # rasterise a typeface without a dependency, and a wrong typeface
    # would be a worse answer than none.
    png(STATIC / "og.png", 1200, 630, mark(1200, 630, 0.26))

    for f in ("favicon.svg", "icon-180.png", "og.png"):
        p = STATIC / f
        print(f"  {f:<16} {p.stat().st_size:>7,} bytes")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
