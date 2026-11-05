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
    # A screenshot is the viewport, so the viewport is made tall enough to
    # hold the page. Anchored views were tried first and photographed
    # blank space: an anchor jump under a virtual clock lands before the
    # images have given the page its height.
    #
    # The hero does not stretch with the window — `min-height:
    # min(82svh, 46rem)` caps it at 46rem — so a tall viewport shows the
    # page as it is, not a distorted one.
    (1280, 3400, "desktop", ""),
    # 500, not 390. Headless Chrome will not give a window narrower than
    # about 500px, so asking for 390 produced a 500px LAYOUT cropped into
    # a 390px image — text cut mid-word, looking exactly like a page with
    # horizontal overflow. It was the picture that was too narrow, not
    # the page.
    #
    # 500 is still below both breakpoints (560 and 800), so this is the
    # phone layout, honestly sized. A true 390 needs device emulation
    # over the DevTools protocol, which needs a client library — a real
    # dependency for a difference of 110px within the same layout.
    (500, 3400, "narrow", ""),
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
            # Pictures only. `scroll-behavior: smooth` never finishes
            # under a virtual clock, so an anchored view photographed the
            # hero instead of the section asked for — six shots of the
            # same screen. Reduced motion makes the jump instant, and
            # settles the reveals, so each picture is the page at rest.
            *( ["--force-prefers-reduced-motion"] if shot else [] ),
            # Let the page's own JavaScript run to completion — the whole
            # point. Three simulated seconds is past `load`, past the
            # cover's fade, and past every failsafe that matters.
            # Longer for a picture than for an assertion. The virtual
            # clock can run out before the photographs have finished
            # downloading, and a screenshot with empty image slots looks
            # exactly like a page whose images are broken — it has twice
            # nearly had a non-bug reported.
            f"--virtual-time-budget={10000 if shot else 3000}",
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

    # NOT asserted: whether a split headline has been released.
    #
    # The `in` class is added inside requestAnimationFrame, and whether
    # that frame runs before --dump-dom captures the page is a race the
    # harness cannot control: the same page gives `split in` at a 1000ms
    # virtual-time budget, `split` at 3000ms, and `split in` again at
    # 8000ms. An assertion over that tests a coincidence, and a check
    # that can fail while the code is right is as useless as one that
    # passes while it is wrong — it only teaches you to ignore it.
    #
    # The screenshots show whether the headline arrived. That is the
    # right instrument for a one-frame question.

    return bad


def build_live_config(out: Path) -> Path:
    """config.toml with `live = true`, for rendering only.

    The launch configuration is the only one that will ever face the
    public, and until this existed it was the only one nobody had
    rendered. It is how "STAND-IN" came within one merge of being
    printed across the client's own photographs: the badge was tied to
    the presence of an image, not to whether that image was a
    placeholder, and no check could see it because no check ever built
    the page that would show it.

    Written beside the build, never over config.toml.
    """
    text = (ROOT / "config.toml").read_text(encoding="utf-8")
    live = out / "config.live.toml"
    live.write_text(text.replace("live = false", "live = true"), encoding="utf-8")
    return live


def check_live(html: str) -> "list[str]":
    """What must be true of the page the public would get."""
    bad = []

    if "noindex" in html:
        bad.append("live: still noindex — the page would never be found")
    if "data-palette-toggle" in html:
        bad.append("live: the palette toggle is on the published page")
    # The BADGE, not the words. The demo's placeholder alt text reads
    # "Stand-in photograph…", so matching the phrase anywhere made a
    # check that could never pass — and a check that always fails is
    # read once and ignored afterwards.
    #
    # The badge is the thing that nearly shipped: it was tied to the
    # presence of an image rather than to whether the image was a
    # placeholder, so on launch day it would have been printed across
    # the client's own photographs.
    if 'class="stand-in"' in html or "class=stand-in" in html:
        bad.append(
            "live: the stand-in badge is on the published page — it would "
            "sit on the client's own photographs"
        )
    if "class=\"skip\"" not in html and "class=skip" not in html:
        bad.append("live: no skip link")
    if "<main" not in html:
        bad.append("live: no main landmark")

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
                if name.startswith("narrow") and open_menu:
                    problems.append("narrow: the nav is open before anyone asked")
            # And the configuration that will face the public.
            live_cfg = build_live_config(out)
            built = subprocess.run(
                ["zola", "--config", str(live_cfg), "build",
                 "--base-url", url, "-o", str(out), "-f"],
                cwd=ROOT, capture_output=True, text=True,
            )
            if built.returncode != 0:
                problems.append("the site does not build with live = true")
            else:
                live_html = dom(chrome, url, 1280, 900)
                problems += check_live(live_html)
                dom(chrome, url, 1280, 3400, shots / "launch-page.png")

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
