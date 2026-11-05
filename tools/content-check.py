#!/usr/bin/env python3
"""The client's own publication rules, enforced by the build.

    python3 tools/content-check.py

The brief is strict about what may not reach a published page, and every
one of those rules is the kind that gets forgotten at the exact moment it
matters — the afternoon the site goes live. So they are checks, not
paragraphs:

  * no professional role is published before it has been verified
    (brief §4.04 and §8: "rôles vérifiés avant publication"), and
    "verified" means a dated record of what was checked against — not
    a flag someone remembers flipping
  * no placeholder email address, ever (brief §4.08)
  * no social link that goes nowhere, and no brand mark pointed at
    the service's own homepage instead of the client's profile
  * no stand-in photograph on a live site (NOTICE)
  * no legal notice with blanks in it, and the icons exist
  * nothing still carrying the studio's "To be written" placeholder
  * concepts in development stay marked as such (brief §4.05)

While `live = false` these are warnings: the demo is allowed to be
incomplete, and saying so is the point. The moment `live = true` they
become errors and the build stops.
"""

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent


# Reading TOML is shared — see tools/toml_read.py for why.
from toml_read import value as value_in, front_matter, flag  # noqa: E402


def main() -> int:
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")
    live = flag(cfg, "live")
    fm = front_matter(ROOT / "content" / "_index.md")

    problems: list[str] = []
    # A brand leak is never a warning: it is wrong at live = false too,
    # because a committed file is readable whatever the page renders.
    leaks: list[str] = []

    # --- roles, verified or not ------------------------------------------
    # Counted off the [[extra.work]] blocks rather than parsed as TOML, so
    # this needs no dependency and no Python version that ships one.
    entries = re.findall(r"\[\[extra\.work\]\](.*?)(?=\n\[\[|\Z)", fm, re.S)
    unverified = []
    for e in entries:
        name = re.search(r'name\s*=\s*"([^"]*)"', e)
        name = name.group(1) if name else "?"
        if re.search(r"verified\s*=\s*false", e):
            unverified.append(name)
            continue
        # Claimed as verified. A flag on its own is somebody's word, so
        # the record has to say when it was checked and against what —
        # otherwise "verified" means nothing and the gate it opens is
        # worth nothing either.
        when = re.search(r'verified_on\s*=\s*"([^"]*)"', e)
        what = re.search(r'evidence\s*=\s*"([^"]*)"', e)
        missing = []
        if not (when and when.group(1).strip()):
            missing.append("verified_on")
        if not (what and what.group(1).strip()):
            missing.append("evidence")
        if missing:
            problems.append(
                f"{name}: verified = true but no "
                + " and no ".join(missing)
                + " — a flag without a record is not a verification"
            )
        elif not re.match(r"^\d{4}-\d{2}-\d{2}$", when.group(1).strip()):
            problems.append(
                f"{name}: verified_on is {when.group(1)!r}, expected YYYY-MM-DD"
            )

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

    # --- elsewhere: the two links the client named -------------------------
    # LinkedIn and WhatsApp Business, and both marks carry the same
    # condition from their owners: the mark links to YOUR OWN presence on
    # the service. Pointed at the service's own homepage it is no longer
    # a link, it is decoration, which neither brand's terms permit — so
    # the bare homepage is rejected as firmly as an empty field. The mark
    # file has to be there too: an alt-less broken image in the footer is
    # the one outcome worse than no icon.
    homepages = re.compile(r"^https?://(www\.)?(linkedin\.com|whatsapp\.com)/?$", re.I)
    for who, block in re.findall(
        r"\[extra\.social\.(\w+)\](.*?)(?=\n\[|\n# ----|\Z)", cfg, re.S
    ):
        name = (re.search(r'name\s*=\s*"([^"]*)"', block) or [None, who])[1]
        url = (re.search(r'url\s*=\s*"([^"]*)"', block) or [None, ""])[1]
        mark = (re.search(r'mark\s*=\s*"([^"]*)"', block) or [None, ""])[1]
        if not url:
            problems.append(f"{name} link not configured (config.toml, extra.social)")
            continue
        if homepages.match(url):
            problems.append(
                f"{name} points at the service's homepage, not a profile — "
                "the mark is licensed as a link to our own presence there"
            )
        if who == "whatsapp" and not re.match(r"^https://wa\.me/\d{6,}$", url):
            problems.append(f"{name} link is not a wa.me business number: {url}")
        if mark and not (ROOT / "static" / "img" / "brand" / mark).exists():
            problems.append(
                f"{name} is linked but static/img/brand/{mark} is missing — "
                "download it from the owner's own brand page (see NOTICE)"
            )

    # --- objects the editor created and nobody finished --------------------
    # A new object cannot be blank — objects.py fails on an empty
    # required field — so the studio fills it with text that says it is
    # unfinished. This is the other half of that bargain: the words are
    # allowed to exist, and not allowed to be published.
    for kind, array in (("reference", "extra.work"), ("capability", "extra.services"),
                        ("concept", "extra.concepts"), ("pillar", "extra.about_pillars")):
        for i, block in enumerate(re.findall(rf"\[\[{re.escape(array)}\]\](.*?)(?=\n\[\[|\n# ----|\Z)", fm, re.S), 1):
            if "To be written" in block:
                name = re.search(r'name\s*=\s*"([^"]*)"', block)
                problems.append(
                    f"{kind} {i} ({name.group(1) if name else '?'}) is still "
                    "the placeholder the studio created — write it or remove it"
                )

    # --- the legal notice -------------------------------------------------
    # Required of a publisher established in France whoever the audience
    # is, and a notice with gaps in it is worse than an honest absence —
    # so the blanks block `live` rather than being published as blanks.
    for field in ("entity", "status", "registration", "address", "publisher"):
        if not value_in(cfg, field):
            problems.append(f"legal notice incomplete: {field} is empty")

    for f in ("favicon.svg", "icon-180.png", "og.png"):
        if not (ROOT / "static" / f).exists():
            problems.append(f"static/{f} is missing (python3 tools/icons.py)")

    # --- the saveable contact ---------------------------------------------
    # Offered on the page only when a name is configured, so the failure
    # being guarded is the opposite one: a card promised and missing.
    if re.search(r'^vcard_name\s*=\s*"(?!")', cfg, re.M) and not (ROOT / "static" / "contact.vcf").exists():
        problems.append(
            "vcard_name is set but static/contact.vcf is missing "
            "(python3 tools/vcard.py)"
        )

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
