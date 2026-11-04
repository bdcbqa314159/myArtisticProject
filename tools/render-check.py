#!/usr/bin/env python3
"""Does the page actually work when a browser runs it?

    python3 tools/render-check.py

Every other check here reads the source. This one builds the site,
serves it, and lets a real browser execute it — then asks whether what
came out the other end is a working page.

It exists because of a week in which every defect that reached the
client was invisible to everything else: a page that appeared and then
blanked itself, a cover that came back after it had gone, a desktop
navigation bar with no links in it, grids wider than the screen. Each
one was correct code. None was visible to a type checker, a diff, or a
build.

NO DEPENDENCY. It drives whatever Chrome is already on the machine —
`--dump-dom` runs the page's JavaScript and prints the result. GitHub's
ubuntu runners ship Chrome, so CI always has one. A machine without one
skips the check and says so, rather than failing for the wrong reason.
"""

import http.server
import shutil
import socketserver
import subprocess
import sys
from typing import Optional
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8731

CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]

# (width, height, name, anchor)
#
# A screenshot is the viewport, not the page, so the sections below the
# fold need their own. These are the ones carrying the offsets, which
# cannot be reviewed from a picture of the hero.
SIZES = [
    (1280, 900, "desktop-hero", ""),
    (1280, 900, "desktop-expertise", "#services"),
    (1280, 900, "desktop-work", "#work"),
    (1280, 900, "desktop-about", "#about"),
    (390, 844, "phone-hero", ""),
    (390, 844, "phone-work", "#work"),
]


def find_chrome() -> Optional[str]:
    for c in CHROMES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def dom(chrome: str, url: str, width: int, height: int, shot: Path = None) -> str:
    """Render the page and return the DOM. With `shot`, also save a picture.

    The picture is the point of running a browser at all: the DOM says
    whether the page is broken, and only an image says whether it looks
    right. In CI it is uploaded as an artifact, which is how a layout
    can be reviewed by someone who cannot run a browser locally."""
    return subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={width},{height}",
            *( [f"--screenshot={shot}"] if shot else [] ),
            # Let the page's own JavaScript run to completion — the whole
            # point. Three simulated seconds is past `load`, past the
            # cover's fade, and past every failsafe that matters.
            "--virtual-time-budget=3000",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    ).stdout


def check(html: str, where: str) -> "list[str]":
    """What must be true of a page a browser has finished with."""
    bad = []

    if 'class="js' not in html and "class='js" not in html and " js" not in html[:400]:
        bad.append(f"{where}: the script never ran — nothing else here means anything")

    # The cover. Both halves: the class that shows it, and the element.
    if "booting" in html[:400]:
        bad.append(f"{where}: still `booting` — the page was never shown")
    if 'class="loader"' in html:
        bad.append(
            f"{where}: the cover is still in the document. It should be removed, "
            "not hidden — a cover that is merely hidden can come back, and did"
        )

    # The headline. Split and released, or the hero opens empty.
    if 'class="split' in html and "split in" not in html:
        bad.append(f"{where}: the headline was split and never released")

    return bad


def main() -> int:
    chrome = find_chrome()
    if not chrome:
        print("\n  no Chrome on this machine — render check skipped.")
        print("  (CI always has one, so this still runs on every push.)\n")
        return 0

    out = Path(tempfile.mkdtemp(prefix="render-check-"))
    url = f"http://127.0.0.1:{PORT}"
    try:
        build = subprocess.run(
            ["zola", "build", "--base-url", url, "-o", str(out), "-f"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if build.returncode != 0:
            print("\n  the site did not build\n")
            print(build.stderr[-800:])
            return 1

        handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(
            *a, directory=str(out), **k
        )
        socketserver.TCPServer.allow_reuse_address = True
        server = socketserver.TCPServer(("127.0.0.1", PORT), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        shots = ROOT / "render-shots"
        shots.mkdir(exist_ok=True)

        problems = []
        try:
            for w, h, name, anchor in SIZES:
                html = dom(chrome, url + anchor, w, h, shots / f"{name}.png")
                if not html.strip():
                    problems.append(f"{name}: the browser returned nothing")
                    continue
                problems += check(html, name)

                # The bar, which is different at each size and has been
                # wrong at both: inline links above 800px, a disclosure
                # below it.
                open_menu = "<details" in html and " open" in html.split("<details")[1][:80]
                if name.startswith("desktop") and not open_menu:
                    problems.append(
                        "desktop: the nav is closed, so the bar has no links in it"
                    )
                if name.startswith("phone") and open_menu:
                    problems.append("phone: the nav is open before anyone asked")
        finally:
            server.shutdown()

        if problems:
            print("\n  RENDERED PAGE IS WRONG\n")
            for p in problems:
                print(f"    - {p}")
            print()
            return 1

        print(f"\n  render: the page works, {len(SIZES)} views checked")
        for f in sorted(shots.glob("*.png")):
            print(f"  {f.name}  {f.stat().st_size:,} bytes")
        print()
        return 0
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
