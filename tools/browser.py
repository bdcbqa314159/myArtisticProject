#!/usr/bin/env python3
"""Driving a headless browser, and nothing else.

Lifted out of `tools/render-check.py`, which was 2345 lines holding
three unrelated jobs: finding and running a browser, building variants
of the site to run it against, and the twenty-five checks themselves.
This is the first of those.

What is known about this browser is written down here because it is
counter-intuitive and was learned the hard way:

  * animation frames run at the TOP LEVEL but not inside an iframe, so
    anything measuring motion has to drive the page from a frame and
    anything waiting for a frame inside one waits for ever;
  * `--virtual-time-budget` expiring looks exactly like a probe that
    found nothing;
  * the viewport floors at 500px, so a 390px phone is really 500px and
    must be framed at 390 to be measured;
  * `prefers-color-scheme: dark` is the default.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent


CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def find_chrome() -> Optional[str]:
    for c in CHROMES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def dom(chrome: str, url: str, width: int, height: int, shot: Path = None,
        no_js: bool = False, reduced: bool = False, budget: int = 0) -> str:
    """Render the page and return the DOM. With `shot`, also save a picture.

    The picture is the point of running a browser at all: the DOM says
    whether the page is broken, and only an image says whether it looks
    right. In CI it is uploaded as an artifact, which is how a layout
    can be reviewed by someone who cannot run a browser locally."""
    off = ["--disable-javascript"] if no_js else []
    return subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            # SCROLLBARS THAT TAKE SPACE, like the runner's.
            #
            # macOS overlays them and Linux does not, so a box's content
            # is up to 15px shorter there than here — and a rule
            # measured against `100vh` rather than against the box it
            # sits in came out right locally and wrong on CI: "39px of
            # ground above the open photograph" where the band is 44.
            # A real difference on a real platform, invisible on this
            # one.
            #
            # Matching the runner makes that class of failure local, and
            # it is the stricter of the two: a layout that holds while
            # scrollbars take room holds when they take none.
            "--disable-features=OverlayScrollbar",
            "--no-sandbox",
            f"--window-size={width},{height}",
            *( [f"--screenshot={shot}"] if shot else [] ),
            # Pictures only. `scroll-behavior: smooth` never finishes
            # under a virtual clock, so an anchored view photographed the
            # hero instead of the section asked for — six shots of the
            # same screen. Reduced motion makes the jump instant, and
            # settles the reveals, so each picture is the page at rest.
            # Also asked for explicitly by probes that drive the page:
            # the scroll runs on animation frames this browser does
            # not run, and under reduced motion it is a jump that
            # reports its end, so a chain hanging off that end
            # becomes observable.
            *( ["--force-prefers-reduced-motion"] if shot or reduced else [] ),
            # Let the page's own JavaScript run to completion — the whole
            # point. Three simulated seconds is past `load`, past the
            # cover's fade, and past every failsafe that matters.
            # Longer for a picture than for an assertion. The virtual
            # clock can run out before the photographs have finished
            # downloading, and a screenshot with empty image slots looks
            # exactly like a page whose images are broken — it has twice
            # nearly had a non-bug reported.
            *off,
            # A probe that waits for the page to be READY rather than for
            # a fixed delay needs longer than the default: the cover has
            # its own floor, and the clock stopping mid-probe looks
            # exactly like a probe that found nothing.
            f"--virtual-time-budget={budget or (10000 if shot else 3000)}",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    ).stdout
