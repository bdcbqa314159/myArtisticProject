#!/usr/bin/env python3
"""The stylesheet against the page it styles.

    python3 tools/css-check.py

TWO QUESTIONS, both of which went unasked until an audit asked them.

ONE: does every class the stylesheet styles exist anywhere? Forty-four
lines of rules for `.project[open]` were still here long after `.shots`
replaced that level — a whole gallery level's worth of CSS, styling
nothing, read by everyone who came after as if it mattered.

TWO: do the custom properties written by script and read by the
stylesheet agree? `--horizon`, `--bow`, `--from-y`, `--done` are set in
TypeScript and read in CSS, and nothing in either language mentions the
other. Rename one side and the page keeps working with that rule
silently doing nothing — which is exactly how a carousel loses its
horizon, or a heading its arc.

WHAT COUNTS AS "EXISTS". A class may be written in the templates, added
by the script, or named in the allowlist below with the reason it is
not in either — a state the page only reaches with content it does not
have yet, or markup the browser builds for us.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "static" / "css" / "site.css"

# Styled, and legitimately absent from both the templates and the
# script. Each needs a reason; without one it is dead CSS.
EXPECTED_ABSENT = {
    "js":      "put on <html> by the inline script in the head, which is not "
               "part of src/",
    "filters": "the SVG filter the smear draws into, built by motion.ts as "
               "markup rather than by classList",
    "credit":  "half of `.credit-studio`, which is in the footer — the "
               "selector reader here splits on the hyphen",
}


def classes_in(text: str) -> "set[str]":
    found: "set[str]" = set()
    for m in re.finditer(r'class=("([^"]*)"|\'([^\']*)\'|([^\s>]+))', text):
        found |= set((m.group(2) or m.group(3) or m.group(4) or "").split())
    return found


def main() -> int:
    css = re.sub(r"/\*.*?\*/", "", SHEET.read_text(encoding="utf-8"), flags=re.S)
    scripts = " ".join(p.read_text(encoding="utf-8") for p in (ROOT / "src").glob("*.ts"))
    # Tera first: a class attribute is often half template —
    # `class="meta{% if not w.verified %} role-unverified{% endif %}"` —
    # and an extractor that cannot read that reports live classes as
    # dead, which is how this check would have taught people to ignore
    # it in its first week.
    templates = " ".join(p.read_text(encoding="utf-8")
                         for p in (ROOT / "templates").glob("*.html"))
    templates = re.sub(r"\{%.*?%\}|\{\{.*?\}\}", " ", templates, flags=re.S)

    present = classes_in(templates)
    present |= set(re.findall(r'classList\.(?:add|remove|toggle|contains)\("([a-z-]+)"',
                              scripts))
    present |= set(re.findall(r'className = "([a-z0-9 -]+)"', scripts)
                   and " ".join(re.findall(r'className = "([a-z0-9 -]+)"', scripts)).split()
                   or [])
    present |= set(re.findall(r'class="([a-z0-9 -]+)"', scripts))

    styled = set(re.findall(r"\.([a-z][a-z0-9-]+)", css))
    orphans = sorted(styled - present - set(EXPECTED_ABSENT))

    bad = []
    if orphans:
        bad.append(
            "the stylesheet styles " + ", ".join("." + c for c in orphans)
            + " — not in the templates, not touched by the script. Either it "
            "is dead, or it belongs in EXPECTED_ABSENT here with the reason "
            "it cannot be found")

    # And the other way: an allowlisted class that HAS turned up can stop
    # being an exception.
    stale = sorted(c for c in EXPECTED_ABSENT if c in present)
    if stale:
        bad.append(
            "these are listed as absent on purpose and are now in the page "
            "or the script: " + ", ".join(stale) + ". Take them off the list")

    # ---- the custom properties, both directions ---------------------
    read = set(re.findall(r"var\(--([a-z-]+)", css))
    declared = set(re.findall(r"--([a-z-]+)\s*:", css))
    written = set(re.findall(r'setProperty\("--([a-z-]+)"', scripts))

    lost = sorted(read - declared - written)
    if lost:
        bad.append(
            "the stylesheet reads " + ", ".join("--" + p for p in lost)
            + ", which nothing declares and no script writes. A rule that "
            "resolves to nothing is a rule that quietly does nothing")

    unread = sorted(written - read)
    if unread:
        bad.append(
            "the script writes " + ", ".join("--" + p for p in unread)
            + ", which the stylesheet never reads. Either the rule that used "
            "it has gone, or one side was renamed")

    if bad:
        print("\n  THE STYLESHEET AND THE PAGE DISAGREE\n")
        for b in bad:
            print(f"    - {b}\n")
        return 1

    print(f"\n  css: {len(styled)} classes all accounted for, "
          f"{len(written)} properties written by script and read by the "
          f"stylesheet\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
