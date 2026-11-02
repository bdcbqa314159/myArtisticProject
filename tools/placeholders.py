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


def fetch() -> int:
    written = []
    for name, seed, w, h in WANTED:
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
    sys.exit(purge() if "--purge" in sys.argv[1:] else fetch())
