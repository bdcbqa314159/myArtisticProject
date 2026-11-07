#!/usr/bin/env python3
"""The content checker still catches what it is supposed to catch.

    python3 tools/objects-check.py

`objects.py` is what stands between a malformed page and a build. Until
this file existed, nothing stood behind IT: I deleted each of its
cross-reference checks in turn, ran it, and it reported the page well
formed every time — which proved nothing, because the thing being asked
was also the thing being broken.

So each case here feeds a deliberately wrong page to the checker and
requires a refusal, naming what it is about. A checker nobody checks is
a checker that quietly stops checking.

Runs against a copy. The real content file is never touched.
"""

import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import objects                                              # noqa: E402

MARK = "# ---- 04 original concepts"

SOUND = '''
[[extra.project]]
id = "r1-a"
reference = 1
name = "Projet A"

[[extra.photo]]
project = "r1-a"
file = "r1-a-01.png"
alt = "Une description."
'''

CASES = [
    ("two projects sharing an id", "share the id", '''
[[extra.project]]
id = "same"
reference = 1
name = "A"

[[extra.project]]
id = "same"
reference = 2
name = "B"
'''),
    ("a project on a reference that does not exist", "not one of the", '''
[[extra.project]]
id = "r9-a"
reference = 99
name = "A"
'''),
    ("a project whose reference is not a number", "not one of the", '''
[[extra.project]]
id = "r1-a"
reference = "premiere"
name = "A"
'''),
    ("a photograph on no project", "no project has the id", '''
[[extra.project]]
id = "r1-a"
reference = 1
name = "A"

[[extra.photo]]
project = "ghost"
file = "x.png"
alt = "Une description."
'''),
    ("a photograph with no description", "alt is required", '''
[[extra.project]]
id = "r1-a"
reference = 1
name = "A"

[[extra.photo]]
project = "r1-a"
file = "x.png"
alt = ""
'''),
    ("a project with no id", "id is required", '''
[[extra.project]]
id = ""
reference = 1
name = "A"
'''),
    ("a photograph with no file", "file is required", '''
[[extra.project]]
id = "r1-a"
reference = 1
name = "A"

[[extra.photo]]
project = "r1-a"
file = ""
alt = "Une description."
'''),
    ("a misspelt field, which the template would ignore in silence",
     "unknown field", '''
[[extra.project]]
id = "r1-a"
reference = 1
name = "A"
titel = "typo"
'''),
]


def run(page: str, tmp: Path) -> "tuple[int, str]":
    target = tmp / "content" / "_index.md"
    target.write_text(page, encoding="utf-8")
    objects.CONTENT = target
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = objects.check()
    return code, out.getvalue()


def main() -> int:
    bad: "list[str]" = []

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        shutil.copytree(ROOT / "content", tmp / "content")
        original = (tmp / "content" / "_index.md").read_text(encoding="utf-8")
        if MARK not in original:
            print(f"\n  cannot find {MARK!r} in the page — this check is stale\n",
                  file=sys.stderr)
            return 1

        # The page as it stands must pass, or every refusal below is
        # meaningless: a checker that refuses everything is not a checker.
        code, said = run(original, tmp)
        if code != 0:
            bad.append(f"the real page does not pass its own checker: {said.strip()}")

        # ...and so must the page with a sound project and photograph in
        # it, or the new kinds are unusable however well they refuse.
        code, said = run(original.replace(MARK, SOUND + "\n" + MARK, 1), tmp)
        if code != 0:
            bad.append(f"a sound project and photograph were refused: {said.strip()}")

        for what, expect, block in CASES:
            code, said = run(original.replace(MARK, block + "\n" + MARK, 1), tmp)
            if code == 0:
                bad.append(f"{what} — accepted")
            elif expect not in said:
                bad.append(f"{what} — refused, but said {said.strip()[:90]!r}")

        # An empty class is missing, not well formed — except the two
        # that are allowed to be: a site with six references and no
        # projects yet is mid-handover, not broken.
        stripped = original
        for array in ("extra.work", "extra.services"):
            stripped = stripped.replace(f"[[{array}]]", "[[removed]]")
        code, said = run(stripped, tmp)
        if code == 0:
            bad.append("a page with no references and no capabilities passed")

    if bad:
        print("\n  THE CONTENT CHECKER\n")
        for b in bad:
            print(f"    - {b}")
        print()
        return 1

    print(f"\n  objects-check: the checker refuses {len(CASES)} malformed "
          "pages and accepts two sound ones\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
