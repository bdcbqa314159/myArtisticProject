#!/usr/bin/env python3
"""Structural invariants: the things that must be true once, and only once.

    python3 tools/invariants.py

Every defect that reached the client this week was a SEQUENCING or
DUPLICATION defect, not a logic one — motion prepared after the cover
lifted, a blend mode isolated by an opacity threshold, scroll restored
under a cover, and two separate mechanisms both revealing the page.

None of them is visible to a type checker, and none is visible in a
diff: each piece was correct on its own. But duplication is greppable,
and the worst of them — two reveals running in sequence, so the cover
vanished and then came back — would have been caught here the moment it
landed.

This is a cheap instrument, not a substitute for looking at the page.
It catches a specific and recurring class of mistake, which is worth
more than it costs.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# (what it is, file, pattern, how many there must be, why)
INVARIANTS = [
    (
        "one place decides the page is ready",
        "src/landing.ts",
        r'readyState === "complete"',
        1,
        "Two of these ran in sequence once: the first removed `booting`, "
        "which takes the cover away instantly, and the second added "
        "`.is-leaving`, which put it back. Page, loader, page — on every "
        "load, for hours, invisible to every other check here.",
    ),
    (
        "one place shows the loader's leaving state",
        "src/landing.ts",
        r'classList\.add\("is-leaving"\)',
        1,
        "The cover is displayed by `.booting` or by `.is-leaving`. A "
        "second place adding the latter can re-show a cover that has "
        "already gone.",
    ),
    (
        "one cover in the markup",
        "templates/index.html",
        r'class="loader"',
        1,
        "Two overlays cannot be reasoned about, and only one of them "
        "would ever be removed.",
    ),
    (
        "the landing page has a main landmark",
        "templates/index.html",
        r"<main>",
        1,
        "It was dropped when the template was rebuilt for the maquette's "
        "architecture, and nothing noticed for eleven PRs: no skip-to-content "
        "landmark, and §5 asks for semantic HTML. The accessibility checks "
        "looked at alt text, headings and lang, and never at landmarks.",
    ),
    (
        "one Content-Security-Policy, in the shared head",
        "templates/_head.html",
        r'http-equiv="Content-Security-Policy"',
        1,
        "It used to be copied into each template. A policy tightened in "
        "one place and not the other is the kind of difference nobody "
        "notices until it matters.",
    ),
    (
        "the templates do not carry their own policy",
        "templates/index.html",
        r'http-equiv="Content-Security-Policy"',
        0,
        "It belongs in _head.html, included by both.",
    ),
]


def main() -> int:
    problems = []
    for name, rel, pattern, expected, why in INVARIANTS:
        found = len(re.findall(pattern, read(rel)))
        if found != expected:
            problems.append((name, rel, found, expected, why))

    if not problems:
        print(f"\n  invariants: {len(INVARIANTS)} hold\n")
        return 0

    print("\n  INVARIANT BROKEN\n")
    for name, rel, found, expected, why in problems:
        print(f"    {name}")
        print(f"      {rel}: found {found}, expected {expected}")
        print(f"      {why}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
