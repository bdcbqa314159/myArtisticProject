#!/usr/bin/env python3
"""Stand-in photographs, and the one command that removes them.

    python3 tools/placeholders.py          # fetch
    python3 tools/placeholders.py --purge  # remove every one, and the list

Images come from Lorem Picsum, which serves Unsplash photography under
the Unsplash License: free use, no permission needed, no attribution
required. The licence is not why they leave. They leave because a
portfolio built from someone else's photographs misrepresents the artist
whose name is on it — see NOTICE.

Every file written is recorded in content/PLACEHOLDERS.txt, so --purge
has a list rather than a guess, and a real photograph dropped in later
can never be deleted by it.
"""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "content" / "PLACEHOLDERS.txt"

# Seeds, not random: the same request returns the same photograph, so a
# layout reviewed yesterday is the layout reviewed today. Sizes are the
# shapes the page actually uses — a wide fragment and a portrait.
WANTED = [
    ("fragment-01.jpg", "10m-set", 1600, 1067),
    ("fragment-02.jpg", "10m-stage", 1600, 1067),
    ("fragment-03.jpg", "10m-studio", 1600, 1067),
    ("fragment-04.jpg", "10m-rehearsal", 1067, 1600),
]

# The portfolio inside each reference: how many projects, and how many
# photographs in each. Smaller than the drop-in fixture on purpose —
# these are COMMITTED, so every one of them is weight in the repository
# for as long as the demo stands. Enough to show what the gallery does,
# not a stress test; the stress test lives in `_dropin/`, which nobody
# clones.
#
# 1200px wide because the template resizes to 1100: larger is bytes
# nobody is served.
# Up to five projects on a reference's fridge — one large and four laid
# over it — and up to five photographs in each. Fewer is allowed and
# shown; more is refused by tools/objects.py, because a sixth would be
# on no page at all.
PROJECTS = [5, 4, 5, 4, 5, 4]
PER_PROJECT = [4, 3, 5, 4, 3]
LETTERS = "abcdef"


def portfolio() -> "list[tuple[str, str, int, int]]":
    out = []
    for ref, many in enumerate(PROJECTS, 1):
        for slot in range(many):
            pid = f"r{ref}-{LETTERS[slot]}"
            for n in range(1, PER_PROJECT[slot] + 1):
                tall = (n % 4 == 0)
                # 1000px wide: the carousel resizes to 1000 and the
                # background to 900, so anything larger is bytes nobody
                # is served — and there are a hundred of them.
                w, h = (750, 1000) if tall else (1000, 667)
                # The seed names nothing and nobody — an earlier set of
                # these carried the client's own mark, in a public
                # repository. See the tripwire in content-check.py.
                out.append((f"work-{pid}-{n:02d}.jpg", f"folio-{ref}{slot}{n}", w, h))
    return out


def blocks() -> str:
    """The TOML for what `portfolio()` fetches, to paste into the page.

    Printed rather than written: this tool fetches files, and what the
    page says is a decision a person makes. The two must match, which is
    why they are generated from the same list.
    """
    out = []
    for ref, many in enumerate(PROJECTS, 1):
        for slot in range(many):
            pid = f"r{ref}-{LETTERS[slot]}"
            out += ["[[extra.project]]", f'id = "{pid}"',
                    f"reference = {ref}",
                    f'name = "Projet {ref}-{LETTERS[slot].upper()}"', ""]
    for name, _seed, _w, _h in portfolio():
        pid = name[len("work-"):].rsplit("-", 1)[0]
        n = name[-6:-4]
        out += ["[[extra.photo]]", f'project = "{pid}"', f'file = "{name}"',
                f'alt = "Photographie {n} — image de remplacement, '
                f'pas le travail du client"', ""]
    return "\n".join(out)


def fetch() -> int:
    written = []
    for name, seed, w, h in WANTED + portfolio():
        dest = ROOT / "content" / name
        url = f"https://picsum.photos/seed/{seed}/{w}/{h}"
        print(f"  {name} <- {url}")
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
        except Exception as exc:                      # offline, or Picsum down
            print(f"    failed: {exc}")
            continue
        # A truncated download that still "succeeds" would be a broken
        # image nobody notices until it is on a phone in front of a client.
        if len(data) < 10_000:
            print(f"    failed: {len(data)} bytes is not a photograph")
            continue
        dest.write_bytes(data)
        written.append(name)

    if not written:
        print("\n  nothing fetched.\n")
        return 1

    # Append rather than replace: a second run with different sizes must
    # not orphan what the first run wrote.
    known = set(LEDGER.read_text().split()) if LEDGER.exists() else set()
    LEDGER.write_text("".join(f"{n}\n" for n in sorted(known | set(written))))
    print(f"\n  {len(written)} placeholder(s). Listed in {LEDGER.relative_to(ROOT)}.")
    print("  Remove them all with: python3 tools/placeholders.py --purge\n")
    return 0


def purge() -> int:
    if not LEDGER.exists():
        print("\n  no placeholder list — nothing was fetched.\n")
        return 0
    gone = 0
    for name in LEDGER.read_text().split():
        p = ROOT / "content" / name
        if p.exists():
            p.unlink()
            gone += 1
            print(f"  removed {name}")
    LEDGER.unlink()
    print(f"\n  {gone} placeholder(s) removed, and the list with them.\n")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--blocks" in args:
        print(blocks())
        sys.exit(0)
    sys.exit(purge() if "--purge" in args else fetch())
