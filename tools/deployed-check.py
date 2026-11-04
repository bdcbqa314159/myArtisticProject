#!/usr/bin/env python3
"""Is what is deployed what we merged?

    python3 tools/deployed-check.py

Every other check here asks whether the code is right. This one asks a
different question, and the only one that matters to the person looking
at the site: **did it actually ship?**

It exists because of an afternoon when four pull requests were merged,
all four passed every check, and the live site stayed three merges
behind — a Pages deployment had stuck on GitHub's side, blocking every
deployment after it with a 400. The build was green, the badge was red
on a page nobody watches, and the thing that noticed was Bernardo
looking at the site.

So: build locally, fetch what is live, and compare the files that
actually decide what a visitor sees.
"""

import hashlib
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files whose content is the site. Not index.html: absolute URLs inside
# it differ between a local build and the deployed one, which would make
# this cry wolf every time.
WATCHED = ["css/site.css", "js/landing.js", "js/words.js"]


def base_url() -> str:
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")
    for line in cfg.splitlines():
        if line.startswith("base_url"):
            return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    return ""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def main() -> int:
    url = base_url()
    if not url or "example.com" in url:
        print("\n  no real base_url configured — nothing to compare against\n")
        return 0

    build = subprocess.run(["zola", "build"], cwd=ROOT, capture_output=True, text=True)
    if build.returncode != 0:
        print("\n  the site does not build locally; fix that first\n")
        return 1

    stale, unreachable = [], []
    for rel in WATCHED:
        local = (ROOT / "public" / rel)
        if not local.exists():
            continue
        try:
            with urllib.request.urlopen(f"{url}/{rel}", timeout=20) as r:
                live = r.read()
        except (urllib.error.URLError, OSError) as exc:
            unreachable.append(f"{rel}: {exc}")
            continue
        a, b = digest(local.read_bytes()), digest(live)
        if a != b:
            stale.append(f"{rel}: built {a}, live {b}")

    if unreachable:
        print("\n  COULD NOT REACH THE SITE\n")
        for u in unreachable:
            print(f"    - {u}")
        print()
        return 1

    if stale:
        print("\n  THE LIVE SITE IS NOT WHAT THIS BUILDS\n")
        for s in stale:
            print(f"    - {s}")
        print("\n  A deployment has failed or is stuck. Check:")
        print("    gh run list --branch main --limit 3")
        print("    gh api repos/<owner>/<repo>/pages -q .status\n")
        return 1

    print(f"\n  deployed: the live site matches this build ({len(WATCHED)} files)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
