#!/usr/bin/env python3
"""Every script written inside another language, parsed.

    python3 tools/embedded-js-check.py

There are around 1,100 lines of browser JavaScript in this repository
that are not in a `.js` file: 11 probe strings inside
`tools/render-check.py`, and the studio panel's entire front end inside
a Python string in `tools/studio/server.py`.

`tsc` never sees them. No linter sees them. A typo in a probe shows up
as "the probe returned no verdict", which at least fails — but a typo
in the panel's 500 lines breaks the editor outright and **nothing here
would notice**, because `studio/check.py` reads those lines as text and
never parses them.

So this parses them. It does not run them and cannot know whether they
are correct; it knows whether they are JavaScript.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where to look, and how to get the script out of it.
# The second pattern named SHELL alone, and the panel has two pages: the
# form page's own two hundred lines of JavaScript were never parsed. The
# tell was this tool reporting an unchanged line count after that script
# had just been edited — so it matches any such string now rather than
# the names someone remembered.
SOURCES = (
    ("tools/render-check.py", r'^([A-Z_]+_PROBE)\s*=\s*"""(.*?)"""'),
    ("tools/studio/server.py", r'^(SHELL|TEMPLATE)\s*=\s*r?"""(.*?)"""'),
)


def scripts() -> "list[tuple[str, str]]":
    out = []
    for rel, pattern in SOURCES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for block in re.finditer(pattern, text, re.S | re.M):
            name, body = block.group(1), block.group(2)
            for i, tag in enumerate(re.finditer(r"<script[^>]*>(.*?)</script>",
                                                body, re.S), 1):
                label = f"{rel}:{name}" + (f" #{i}" if i > 1 else "")
                out.append((label, tag.group(1)))
    return out


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("\n  node is not installed, so nothing could be parsed.\n",
              file=sys.stderr)
        return 1

    found = scripts()
    if not found:
        # The patterns above are the only thing tying this to the files
        # it checks. If a rename makes them match nothing, this would
        # report success over an empty list — which is the failure mode
        # it exists to prevent elsewhere.
        print("\n  no embedded scripts found at all. The patterns in SOURCES "
              "no longer match anything — fix them rather than this.\n",
              file=sys.stderr)
        return 1

    problems = []
    for label, js in found:
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False,
                                         encoding="utf-8") as f:
            f.write(js)
            path = f.name
        try:
            out = subprocess.run([node, "--check", path],
                                 capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        if out.returncode != 0:
            first = [ln for ln in (out.stderr or "").splitlines() if ln.strip()]
            why = next((ln.strip() for ln in first if "Error" in ln),
                       first[0].strip() if first else "would not parse")
            problems.append(f"{label}: {why}")

    if problems:
        print("\n  EMBEDDED SCRIPT WILL NOT PARSE\n")
        for p in problems:
            print(f"    - {p}")
        print()
        return 1

    total = sum(len(js.splitlines()) for _, js in found)
    print(f"\n  embedded js: {len(found)} script(s), {total} lines, all parse\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
