#!/usr/bin/env python3
"""The client's own publication rules, enforced by the build.

    python3 tools/content-check.py

The brief is strict about what may not reach a published page, and every
one of those rules is the kind that gets forgotten at the exact moment it
matters — the afternoon the site goes live. So they are checks, not
paragraphs:

  * no professional role is published before it has been verified
    (brief §4.04 and §8: "rôles vérifiés avant publication")
  * no placeholder email address, ever (brief §4.08)
  * no stand-in photograph on a live site (NOTICE)
  * concepts in development stay marked as such (brief §4.05)

While `live = false` these are warnings: the demo is allowed to be
incomplete, and saying so is the point. The moment `live = true` they
become errors and the build stops.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def front_matter(p: Path) -> str:
    text = p.read_text(encoding="utf-8")
    parts = text.split("+++")
    return parts[1] if len(parts) >= 3 else ""


def main() -> int:
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")
    live = re.search(r"^live\s*=\s*true\s*$", cfg, re.M) is not None
    fm = front_matter(ROOT / "content" / "_index.md")

    problems: list[str] = []
    # A brand leak is never a warning: it is wrong at live = false too,
    # because a committed file is readable whatever the page renders.
    leaks: list[str] = []

    # --- roles, verified or not ------------------------------------------
    # Counted off the [[extra.work]] blocks rather than parsed as TOML, so
    # this needs no dependency and no Python version that ships one.
    entries = re.findall(r"\[\[extra\.work\]\](.*?)(?=\n\[\[|\Z)", fm, re.S)
    unverified = [
        re.search(r'name\s*=\s*"([^"]*)"', e).group(1)
        for e in entries
        if re.search(r"verified\s*=\s*false", e)
    ]
    if unverified:
        problems.append(
            f"{len(unverified)} professional role(s) not verified: "
            + ", ".join(unverified)
        )
    if not entries:
        problems.append("no work entries at all — the brief requires six")
    elif len(entries) != 6:
        problems.append(f"{len(entries)} work entries; the brief names six")

    # --- the contact address ---------------------------------------------
    email = re.search(r'^email\s*=\s*"([^"]*)"', cfg, re.M)
    address = email.group(1) if email else ""
    if not address:
        problems.append("no contact address configured")
    elif re.search(r"example\.(com|org)|@example|placeholder|todo|xxx", address, re.I):
        problems.append(f"placeholder contact address: {address}")

    # --- stand-in photographs --------------------------------------------
    ledger = ROOT / "content" / "PLACEHOLDERS.txt"
    if ledger.exists():
        n = len(ledger.read_text().split())
        problems.append(
            f"{n} stand-in photograph(s) still present "
            "(python3 tools/placeholders.py --purge)"
        )

    # --- concepts stay marked as in development ---------------------------
    for block in re.findall(r"\[\[extra\.concepts\]\](.*?)(?=\n\[\[|\Z)", fm, re.S):
        if not re.search(r"^status\s*=\s*\"", block, re.M):
            name = re.search(r'name\s*=\s*"([^"]*)"', block)
            problems.append(
                f"concept without a status: {name.group(1) if name else '?'} "
                "— a concept must never read as a delivered commission"
            )

    # --- the client's brand must not be in a tracked file -----------------
    # The terms live in _ref/identifiers.txt, which is NOT tracked: a
    # tripwire that names the thing it guards would be the leak it is
    # trying to prevent. Absent (CI, a fresh clone) the check says so and
    # stands down — it is a guard for the machine where a real name could
    # be pasted in, which is this one.
    ids = ROOT / "_ref" / "identifiers.txt"
    if not ids.exists():
        print("  (no _ref/identifiers.txt — brand tripwire not armed here)")
    else:
        terms = [
            line.strip()
            for line in ids.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
        ).stdout.split()
        for rel in tracked:
            f = ROOT / rel
            try:
                body = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue                      # images and the like
            for t in terms:
                if t.lower() in body.lower():
                    leaks.append(
                        f"{rel} contains a protected term ({t!r}) — this "
                        "repository is public"
                    )

    if leaks:
        print("\n  PROTECTED TERMS IN TRACKED FILES — do not commit\n")
        for l in leaks:
            print(f"    - {l}")
        print()
        return 1

    if not problems:
        print("\n  content: every rule the brief sets is satisfied.\n")
        return 0

    head = "REFUSING TO PUBLISH" if live else "not ready to go live (live = false, so this is a warning)"
    print(f"\n  {head}\n")
    for p in problems:
        print(f"    - {p}")
    print()
    return 1 if live else 0


if __name__ == "__main__":
    sys.exit(main())
