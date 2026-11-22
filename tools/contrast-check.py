#!/usr/bin/env python3
"""Can the text be read, and can the fields be seen?

    python3 tools/contrast-check.py

WHY THIS EXISTS NOW

The palette used to be eight hex values in `site.css`, chosen once and
changed by whoever was reading the 2000 lines around them. It is now
eight values in `config.toml` that the studio panel invites a graphiste
to retype, and `tools/theme.py` renders whatever they say into a
stylesheet that wins over the defaults. Nothing computed anything about
the result. A cream half a shade lighter, or a grey half a shade
warmer, and the body text of the whole site drops below the threshold
where someone with ordinary middle-aged eyesight can read it — and the
only signal would be a visitor who never says so.

So this is arithmetic, not opinion: WCAG 2.1 relative luminance, the
ratios every pair of tokens that actually meets on the page produces,
and the floor each pair has to clear.

    1.4.3 Contrast (Minimum)  4.5:1 for body text
    1.4.11 Non-text Contrast  3:1 for the visible boundary of a control

THE ONE THAT IS NOT A PREFERENCE

`--line` is 1.3:1 against the ground in every palette, which is right
for a hairline between sections — a decorative rule is explicitly
exempt — and was wrong for the only thing marking the edge of a text
field. A field whose underline is 1.3:1 has, for a low-vision reader,
no edge at all: nothing says where to type. That is what this found on
its first run, and the last check here is what stops it coming back.

WHAT IT MODELS

Three palettes ship: cream (the default every visit begins in), cool,
and cool in a dark browser. Each block in `site.css` declares all eight
tokens, so each is checked as a set — and `theme.css` is layered on top
the way a browser layers it, which is the whole point: the values that
matter are the ones a graphiste will put there, not the ones committed
today.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "static" / "css" / "site.css"
THEME = ROOT / "static" / "css" / "theme.css"

TOKENS = ("ink", "muted", "faint", "line", "bg", "panel", "tint", "accent")


def declarations(body: str) -> "dict[str, str]":
    return {
        name: value.strip()
        for name, value in re.findall(r"--([a-z-]+):\s*([^;]+);", body)
        if name in TOKENS
    }


def palettes() -> "dict[str, dict[str, str]]":
    """The three palettes that ship, each as a complete set of tokens.

    Layered in the order a browser would: `site.css` first, then
    `theme.css`, which is linked after it and so wins.

    The dark pairing is worth a word. `site.css` defines it as
    `[data-palette="cool"]` inside a `prefers-color-scheme` block, and
    `theme.css` writes `[data-palette="cool"]` unconditionally — same
    specificity, later sheet. So a graphiste's cool values override the
    dark pairing too, and that is modelled here rather than wished
    away: if they ever set a light cool palette, this check is what
    says that dark-mode visitors now read light text on light ground.
    """
    css = SITE.read_text(encoding="utf-8")

    cream, cool = {}, {}
    for sel, body in re.findall(
            r"(?m)^(:root|\[data-palette=\"cool\"\])\s*\{([^}]*)\}", css):
        (cream if sel == ":root" else cool).update(declarations(body))

    dark = dict(cool)
    for block in re.finditer(r"@media \(prefers-color-scheme: dark\)\s*\{(.*?)\n\}",
                             css, re.S):
        for sel, body in re.findall(
                r"(\[data-palette=\"cool\"\]|:root)\s*\{([^}]*)\}", block.group(1)):
            if sel == '[data-palette="cool"]':
                dark.update(declarations(body))

    # TRACKED, so absent means gone. This stood down quietly and
    # measured whatever palettes the stylesheet happened to carry, which
    # on a page whose grounds live in theme.css is most of the subject.
    if not THEME.exists():
        raise SystemExit(
            f"\n  {THEME.name} is not there, and it is a tracked file. The "
            f"palettes come from it — without it this would check contrast "
            f"against colours the page does not use.\n")

    theme = THEME.read_text(encoding="utf-8")
    for sel, body in re.findall(
            r"(?m)^(:root|\[data-palette=\"cool\"\])\s*\{([^}]*)\}", theme):
        said = declarations(body)
        if sel == ":root":
            cream.update(said)
        else:
            cool.update(said)
            dark.update(said)              # same specificity, later sheet

    return {"cream": cream, "cool": cool, "cool in a dark browser": dark}


def luminance(colour: str) -> float:
    """WCAG 2.1 relative luminance of a hex colour."""
    hexed = colour.strip().lstrip("#")
    if len(hexed) == 3:
        hexed = "".join(c * 2 for c in hexed)
    if len(hexed) == 8:                    # #rrggbbaa — alpha is not a colour
        hexed = hexed[:6]
    if len(hexed) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", hexed):
        raise ValueError(f"{colour!r} is not a hex colour")
    channels = [int(hexed[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(one: str, other: str) -> float:
    a, b = luminance(one), luminance(other)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


# (foreground, background, floor, what it is on the page)
PAIRS = (
    ("ink", "bg", 4.5, "the body text on the ground"),
    ("muted", "bg", 4.5, "secondary text — a date, a label, a caption"),
    ("faint", "bg", 4.5, "the quietest text, which is still text"),
    ("ink", "panel", 4.5, "text on a card"),
    ("muted", "panel", 4.5, "a card's secondary text"),
    ("ink", "tint", 4.5, "text on a tinted section"),
    ("accent", "bg", 4.5, "an outline button's label and its border"),
    ("bg", "accent", 4.5, "the filled button's label on its fill"),
    # Not text: the resting edge of a text field, and the focus ring
    # both come from --muted, and a control's boundary needs 3:1.
    ("muted", "bg", 3.0, "the edge of a text field, and the focus ring"),
)

# A control's boundary may not be drawn with the decorative hairline —
# the defect this tool found on its first run, written as a rule so it
# cannot come back.
#
# Form fields and buttons only, deliberately. A bordered thumbnail (the
# PDF miniature a concept opens) is identifiable by the picture inside
# it, so its hairline is decoration. A field with a transparent
# background and nothing typed into it yet is identifiable by its edge
# and by nothing else at all.
CONTROLS = re.compile(r"\b(input|textarea|select|\.btn)\b")


def controls_drawn_with_the_hairline() -> "list[str]":
    css = re.sub(r"/\*.*?\*/", "", SITE.read_text(encoding="utf-8"), flags=re.S)
    found = []
    for selector, body in re.findall(r"(?m)^([^{}@/][^{}]*)\{([^}]*)\}", css):
        if not CONTROLS.search(selector):
            continue
        for line in body.splitlines():
            if re.search(r"\bborder[a-z-]*\s*:", line) and "var(--line)" in line:
                found.append(f"{selector.strip()} — {line.strip()}")
    return found


def main() -> int:
    problems, worst = [], {}

    for name, tokens in palettes().items():
        missing = [t for t in TOKENS if t not in tokens]
        if missing:
            problems.append(f"the {name} palette does not define "
                            f"{', '.join(missing)} — nothing can be computed "
                            f"about a token that is not there")
            continue
        for fg, bg, floor, what in PAIRS:
            try:
                got = ratio(tokens[fg], tokens[bg])
            except ValueError as no:
                problems.append(f"{name}: {no}")
                continue
            worst[name] = min(worst.get(name, 99), got)
            if got + 0.005 < floor:
                problems.append(
                    f"{name}: {what} is {got:.2f}:1 "
                    f"({tokens[fg]} on {tokens[bg]}), and needs {floor}:1. "
                    f"Darken --{fg} or lighten --{bg} in "
                    f"{'config.toml' if THEME.exists() else 'site.css'}"
                )

    for where in controls_drawn_with_the_hairline():
        problems.append(
            f"a control is outlined with the decorative hairline: {where}. "
            f"--line is 1.3:1 against the ground on purpose; a field drawn "
            f"with it has no visible edge. Use --muted, which this check "
            f"holds above 3:1"
        )

    if problems:
        print("\n  CONTRAST\n")
        for p in problems:
            print(f"    - {p}")
        print()
        return 1

    print()
    for name in worst:
        print(f"  {name:24} every pair clears its floor, thinnest "
              f"{worst[name]:.2f}:1")
    print(f"\n  contrast: {len(PAIRS)} pair(s) in {len(worst)} palette(s), and "
          f"no control outlined with the hairline\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
