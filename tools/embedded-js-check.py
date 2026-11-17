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
# Where the browser programs live. All of them are HTML files now —
# the probe pages the render check serves, and the studio panel's two
# pages — so there is nothing left to cut out of a Python string.
#
# Directories, not lists of names: a page added without being mentioned
# anywhere is the normal way coverage goes backwards. And each one must
# yield at least one script, because this tool reporting "all parse"
# over a smaller set than yesterday is the failure it exists to
# prevent. It happened: the probes moved out of render-check.py and
# this went from 16 scripts to 2 without a word.
# Each directory must yield scripts; whether the RIGHT pages are there
# is `tools/studio/check.py`'s question, and it names them. This one
# only parses what it finds.
WHERE = (
    ("tools/probes", "the render check's probe pages"),
    ("tools/studio", "the studio panel's own pages"),
)


def tags(label: str, body: str) -> "list[tuple[str, str]]":
    return [
        (label + (f" #{i}" if i > 1 else ""), tag.group(1))
        for i, tag in enumerate(
            re.finditer(r"<script[^>]*>(.*?)</script>", body, re.S), 1)
    ]


def scripts() -> "list[tuple[str, str]]":
    out = []
    for rel, what in WHERE:
        pages = sorted((ROOT / rel).glob("*.html")) if (ROOT / rel).exists() else []
        found = []
        for page in pages:
            found += tags(f"{rel}/{page.name}", page.read_text(encoding="utf-8"))
        if not found:
            print(f"\n  no scripts found in {rel}/ — {what}. If they have "
                  f"moved, point this at them rather than letting it pass "
                  f"over an empty directory.\n", file=sys.stderr)
            raise SystemExit(1)
        out += found
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
