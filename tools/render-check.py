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
import html as html_module
import json
import math
import re
import shutil
import socketserver
import subprocess
import sys
from typing import Optional
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What was here: the browser harness and the site variants. This file is
# the checks now — one function per thing that must be true of the page
# someone actually receives, and `main` at the end running them.
from browser import dom, find_chrome                        # noqa: E402
from variants import (build_live_config, build_with_a_small_strip,  # noqa: E402
                      build_with_a_waiting_project, build_with_projects, build_with_two_faces)
PORT = 8731


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


PROBES = Path(__file__).resolve().parent / "probes"


def probe(name: str) -> str:
    """One probe page, from `tools/probes/`.

    These were fourteen triple-quoted strings in this file — 831 of its
    2345 lines, and not one of them Python. An editor highlighted a
    browser program as text, nothing could parse it without being told
    how to cut it out of a string first, and reading this file meant
    scrolling past the probes to reach the next check.

    They are ordinary HTML files now, and `tools/embedded-js-check.py`
    parses them where they lie.

    One thing to know if you move them again: the escaping is the
    trap. `\\s` inside a Python string is `\s` by the time the
    browser sees it, so copying the SOURCE characters writes the
    escaping twice — which it did, and two probes came back reporting
    a broken page. Extracted through `ast`, which knows the difference.
    """
    page = PROBES / f"{name}.html"
    if not page.exists():
        raise SystemExit(f"\n  no probe called {name!r} in "
                         f"{PROBES.relative_to(ROOT)}\n")
    return page.read_text(encoding="utf-8")


def only_the_verdict(said: str) -> str:
    """Just what the probe WROTE, out of the page the browser handed back.

    THE SENTINEL IS IN THE PROBE'S OWN SOURCE. Every probe ends with
    something like `textContent = "PATCH " + s`, and `--dump-dom`
    returns the `<script>` along with everything else — so a probe that
    produced NO verdict leaves `no verdict` in its element and the
    literal `"PATCH " + s; }` further down the dump. Searching the whole
    dump for `PATCH (...)` sailed past the element and matched the
    SOURCE, which means `if not found` — the guard every one of these
    checks relies on — could not fire.

    Measured, with the carousel renamed out of the page: the patchwork
    check reported four widths called `"`, `+`, `s;` and `}`, and the
    horizon check, whose whole purpose is that carousel, reported
    nothing wrong at all.

    So the element is read, and only the element. An empty string when
    it is not there leaves every `if not found` below exactly as it was
    written, and makes it true.
    """
    found = re.findall(r'<p id="?(?:o|out|verdict)"?>([^<]*)</p>', said)
    return found[0].strip() if found else ""


def check(html: str, where: str) -> "list[str]":
    """What must be true of a page a browser has finished with."""
    bad = []

    if 'class="js' not in html and "class='js" not in html and " js" not in html[:400]:
        bad.append(f"{where}: the script never ran — nothing else here means anything")

    # The cover. Both halves: the class that shows it, and the element.
    if "booting" in html[:400]:
        bad.append(f"{where}: still `booting` — the page was never shown")
    # THE CLASS AS A WORD, not as a whole attribute value.
    #
    # This read `'class="loader"' in html` and could never match. A
    # cover is only ever LEFT BEHIND in its leaving state, so the thing
    # on the page at that moment is `class="loader is-leaving"` — and
    # the literal with its closing quote does not appear in it. The one
    # fault this check exists for was the one it could not see.
    # Measured: hiding the cover instead of removing it passed cleanly.
    if re.search(r'class="[^"]*\bloader\b', html):
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


TALK_BTN = re.compile(r'class="btn(?: primary)? bubble"')
ANY_BTN = re.compile(r'class="?btn[^">]*"?')


# Contact in the navigation band ends at the form.
#
# Driven rather than argued for. The page's scroll runs on animation
# frames, which this browser does not run — so the whole chain would
# hang at the scroll and never reach the form. Under reduced motion the
# scroll is a jump that reports its end synchronously, and the chain
# completes, which is the only reason this is observable at all.
#
# An iframe because the parent needs to click inside a page it did not
# render, and read a dialog's `open` afterwards. Same origin, so it can.


def check_named_spot(chrome: str, out: Path, url: str) -> "list[str]":
    """A light where its project asked for it, not where it is tidy."""
    (out / "_spot.html").write_text(probe("named-spot"), encoding="utf-8")
    said = dom(chrome, url + "/_spot.html", 1100, 900)
    said = only_the_verdict(said)
    found = re.search(r"SPOT ([^<]*)", said)
    if not found:
        return ["spot: the probe returned no verdict"]
    verdict = found.group(1).strip()
    bad = []
    if "asked=33 77" not in verdict:
        bad.append(f"spot: the project's named position never reached the "
                   f"markup ({verdict})")
    elif "x=33%" not in verdict or "y=77%" not in verdict:
        bad.append(f"spot: a project named its own spot and the light did not "
                   f"take it ({verdict}). A style ATTRIBUTE will not do it — "
                   f"the policy drops inline style; it has to be written with "
                   f"setProperty")
    elif "left=auto" in verdict:
        bad.append(f"spot: the position arrived and resolved to nothing "
                   f"({verdict})")
    if "untouched=EMPTY" not in verdict:
        bad.append(f"spot: a light with no named spot has one anyway "
                   f"({verdict}) — the default in the stylesheet is what "
                   f"every other light depends on")
    return bad


def check_edges(chrome: str, out: Path, url: str) -> "list[str]":
    """Every picture ends the same way.

    Not a matter of taste once it has been asked for: a page where one
    photograph has a hairline, another a 3px cream outline and a third
    nothing at all reads as unfinished, however good each one looks on
    its own.
    """
    (out / "_edges.html").write_text(probe("edges"), encoding="utf-8")
    said = dom(chrome, url + "/_edges.html", 500, 1000, budget=25000)
    said = only_the_verdict(said)
    found = re.search(r"EDGES ([^<]*)", said)
    if not found:
        return ["edges: the probe returned no verdict"]
    verdict = found.group(1).strip()
    f = dict(kv.split("=", 1) for kv in verdict.split() if "=" in kv)
    bad = []
    if f.get("absent", "none") != "none":
        bad.append(f"edges: {f['absent']} is not on the page, so nothing was "
                   f"measured for it ({verdict})")
    if f.get("kinds") != "1":
        bad.append(f"edges: the pictures end in {f.get('kinds')} different "
                   f"ways ({verdict}). One hairline, everywhere — a page "
                   f"where one photograph has an edge and the next has none "
                   f"reads as unfinished")
    if "none" in [v for k, v in f.items() if k not in ("kinds", "absent")]:
        bad.append(f"edges: a picture has no edge at all ({verdict})")
    return bad


def check_escape(chrome: str, out: Path, url: str) -> "list[str]":
    """The band at the edge of an open focus that takes you back out.

    It was `--gutter` of ground — 23px at 390px, a sliver at the edge
    of a phone where a miss lands on a print and opens its carousel.
    This measures the band in the browser rather than trusting the
    stylesheet, because what matters is what the pointer hits: a ring
    drawn with a clip-path, over the prints and under the carousel.
    """
    # A budget, like every probe that waits for the cover: the reveal
    # is a timer, and virtual time ending early reads as a page that
    # never left its loader — which is what this reported first.
    (out / "_escape.html").write_text(probe("escape"), encoding="utf-8")
    said = dom(chrome, url + "/_escape.html", 500, 1000, budget=22000)
    said = only_the_verdict(said)
    found = re.search(r"ESCAPE (\{[^<]*\})", said)
    if not found:
        return ["escape: the probe returned no verdict"]
    verdict = json.loads(found.group(1))
    if "error" in verdict:
        return [f"escape: the probe threw: {verdict['error']}"]

    bad = []
    if not verdict.get("ring"):
        bad.append("escape: an open focus has no way-out band at all")
    if verdict.get("covers") != verdict.get("viewport"):
        bad.append(
            f"escape: the open focus is {verdict.get('covers')} on a "
            f"{verdict.get('viewport')} screen. It is `position: fixed; "
            f"inset: 0`, so a size that is not the screen means an ancestor "
            f"with a transform became its containing block — the rule this "
            f"page has now met three times. The culprit: "
            f"{verdict.get('containingBlock')}")
    # 44px is the floor, and the band is measured in 2px steps from the
    # edge, so 42 is the smallest reading a 44px band can give.
    thin = {side: n for side, n in (verdict.get("band") or {}).items() if n < 42}
    if thin:
        bad.append(
            f"escape: the way out is thinner than a thumb on "
            f"{', '.join(f'{s} ({n}px)' for s, n in thin.items())}. "
            f"--way-out in site.css sets it; 44px is the floor")
    if not verdict.get("closedByTheBand"):
        bad.append(
            "escape: a click in the band does not close the focus. The band "
            "is hittable and nothing listens to it — which every "
            "measurement above passes happily, so this is the one that "
            "matters")
    if verdict.get("openAfterAPrintWasClicked") is False:
        bad.append(
            "escape: clicking a print in the middle of the focus closed it. "
            "The band is for the edge; the middle belongs to the work")
    if not verdict.get("middleIsAPrint"):
        bad.append(
            "escape: the middle of an open focus no longer belongs to the "
            "prints — the band has eaten the whole box, so a click meant to "
            "open a project closes the focus instead")
    return bad


def check_reach(chrome: str, out: Path, url: str) -> "list[str]":
    """Keyboard reach, accessible names, and holding still when asked.

    Two runs of the same probe, which is the point: the second asks the
    browser for reduced motion, and the pair separates "nothing is
    animating" from "this browser never animates anything". Without the
    first run as a control, the second would pass on a page whose
    motion had been deleted outright.
    """
    (out / "_reach.html").write_text(probe("reach"), encoding="utf-8")

    def verdict(reduced: bool) -> dict:
        said = dom(chrome, url + "/_reach.html", 500, 900, reduced=reduced)
        said = only_the_verdict(said)
        found = re.search(r"REACH (\{[^<]*\})", said)
        return json.loads(found.group(1)) if found else {}

    moving, still = verdict(False), verdict(True)
    if not moving or not still:
        return ["reach: the probe returned no verdict"]
    for which, said in (("moving", moving), ("still", still)):
        if "error" in said:
            return [f"reach: the probe threw in the {which} run: {said['error']}"]

    bad = []
    if said_positive := moving.get("positive"):
        bad.append(f"reach: {len(said_positive)} element(s) carry a positive "
                   f"tabindex ({', '.join(said_positive)}). It takes them out "
                   f"of document order and nobody maintaining the page can "
                   f"predict where the keyboard goes next")
    if not moving.get("firstIsSkip"):
        bad.append("reach: the skip link is not the first thing a keyboard "
                   "reaches, so it skips nothing")
    if not moving.get("skipTarget"):
        bad.append("reach: the skip link points at an id that is not on the "
                   "page")
    if moving.get("landed") == "_trap":
        bad.append("reach: opening the form puts the cursor in the honeypot. "
                   "tabindex=\"-1\" does not stop showModal() choosing it — "
                   "anyone typing straight away fills the trap field and "
                   "their message is refused as a robot's")
    elif moving.get("landed") in ("nothing", "no box"):
        bad.append(f"reach: opening the form focuses {moving.get('landed')} — "
                   f"a keyboard is left outside a modal it cannot leave")
    if anonymous := moving.get("anonymous"):
        bad.append(f"reach: {len(anonymous)} control(s) have no accessible "
                   f"name ({', '.join(anonymous)}) — a screen reader reads "
                   f"them as \"link\" and \"button\"")

    # The control, and then the thing being checked.
    if not moving.get("running"):
        bad.append("reach: nothing is animating even without reduced motion, "
                   "so the stillness below proves nothing. Either the page "
                   "lost its motion or this probe can no longer see it")
    elif still.get("running"):
        bad.append(f"reach: {still['running']} animation(s) are still running "
                   f"under prefers-reduced-motion, out of "
                   f"{moving['running']} — the stylesheet has 17 blocks "
                   f"promising otherwise")
    return bad


def check_menu(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_menu.html").write_text(probe("menu"), encoding="utf-8")
    # NOT under reduced motion, deliberately. The page's scroll runs on
    # animation frames this browser does not run, so a journey started
    # here never settles — which makes this the distinguishing
    # experiment for the thing that was asked for: the form must open AT
    # ONCE, not when the scroll lands. Opened on arrival, it would never
    # open here at all.
    said = dom(chrome, url + "/_menu.html", 500, 900)
    said = only_the_verdict(said)
    found = re.search(r"MENU ([^<]*)", said)
    if not found:
        return ["menu: the probe returned no verdict"]
    verdict = found.group(1).strip()
    bad = []
    if "contact=true" not in verdict:
        bad.append(f"menu: Contact in the band does not open the form "
                   f"({verdict})")
    if "control=false" not in verdict:
        bad.append(f"menu: a band link that is not Contact opens the form too "
                   f"({verdict})")
    if "flat=0" not in verdict:
        bad.append(f"shape: an opener has lost its border or its padding — it "
                   f"is no longer drawn as a button ({verdict})")
    if "lands=email" not in verdict:
        bad.append(f"form: opening it does not put the cursor in the address "
                   f"field. If it lands in `_trap` the visitor fills the bot "
                   f"honeypot and their message is dropped in silence "
                   f"({verdict})")
    if "ring=no" not in verdict:
        bad.append(f"form: the browser is drawing its own focus ring on the "
                   f"open form ({verdict})")
    return bad


# Every palette puts a mark its ground can show.
#
# The marks used to follow `prefers-color-scheme`, which answers a
# different question: what the reader's MACHINE prefers, not what colour
# this page's ground actually came out. The two part company on the
# cream palette, which keeps its pale ground in the dark — measured at
# ground luma 242 wearing a white mark, which is a mark nobody can see.


def check_marks(chrome: str, out: Path, url: str, css: str) -> "list[str]":
    """Measured: what shows, against the ground it shows on."""
    names = sorted(set(re.findall(r'\[data-palette="([a-z]+)"\]', css)))
    (out / "_marks.html").write_text(
        probe("marks").replace("__PALETTES__", json.dumps([""] + names)),
        encoding="utf-8")
    said = dom(chrome, url + "/_marks.html", 500, 900)
    said = only_the_verdict(said)
    found = re.search(r"MARKS links=(\d+) ([^<]*)", said)
    if not found:
        return ["marks: the probe returned no verdict"]
    links, verdict = int(found.group(1)), found.group(2).strip()
    bad = []
    if links == 0:
        return ["marks: there are no social links on the page to check"]
    for word in verdict.split():
        name, _, state = word.partition(":")
        if "WRONG" in state:
            bad.append(f"marks: the {name} palette shows a mark its own ground "
                       f"cannot show — white on a pale ground, or black on a "
                       f"dark one ({verdict})")
        if "COUNT" in state:
            bad.append(f"marks: the {name} palette shows the wrong NUMBER of "
                       f"marks — both tones at once, or none ({verdict})")
    return bad


def check_marks_declared(css: str) -> "list[str]":
    """Structural: choosing a ground means choosing the marks for it.

    This is the whole reason the marks moved off `prefers-color-scheme`.
    A palette is a block that sets `--bg`; if it may set a ground without
    saying which marks go on it, the two can drift apart again — and the
    drift is invisible until someone looks at that palette on a real
    screen, which is how the last one was found."""
    bad = []
    for block in re.findall(r"\{([^{}]*)\}", css):
        if "--bg:" not in block:
            continue
        for token in ("--mark-for-light", "--mark-for-dark"):
            if token not in block:
                ground = re.search(r"--bg:\s*([^;]+);", block)
                bad.append(
                    f"css: a palette sets a ground "
                    f"({ground.group(1).strip() if ground else '?'}) without "
                    f"setting `{token}`. Every block that chooses `--bg` must "
                    f"choose the marks that go on it")
    return bad


# The two phrases draw a C.
#
# Driven, not argued for: the animation is PAUSED and its `currentTime`
# is set by hand, so the path is read out of the browser's own
# interpolation without a single animation frame — which is just as
# well, because none run inside an iframe.
#
# What a check has to be able to see here is the difference between an
# arc and the straight diagonal it replaced. A straight line between the
# same two points has no sideways excursion at all, so the depth of the
# bow against the length of the travel is the whole measurement.


def check_arc(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_arc.html").write_text(probe("arc"), encoding="utf-8")
    said = dom(chrome, url + "/_arc.html", 1000, 900)
    said = only_the_verdict(said)
    found = re.search(r"ARC ([^<]*)", said)
    if not found:
        return ["arc: the probe returned no verdict"]
    bad = []
    for word in found.group(1).split():
        width, _, rest = word.partition(":")
        if "=" not in rest:
            bad.append(f"arc: at {width}px the probe could not run — {rest}")
            continue
        f = dict(kv.split("=") for kv in rest.split(":"))
        bow, travel = float(f["bow"]), float(f["travel"])

        # A C, not an I. A straight diagonal between the same two points
        # has no excursion at all, so this is the assertion that tells
        # the new motion from the one it replaced.
        if travel < 1:
            bad.append(f"arc: at {width}px the phrases do not travel at all")
        elif bow / travel < 0.25:
            bad.append(f"arc: at {width}px the path is nearly straight — bow "
                       f"{bow:.0f}px against {travel:.0f}px of travel. That is "
                       f"the italic I again, not a C")

        # A C opens to the RIGHT, so the stroke only ever goes left.
        if f["right"] != "0":
            bad.append(f"arc: at {width}px the path swings right ({f['right']} "
                       f"samples) — that draws a reversed C")

        # The page clips at its edge; an arc that overruns it takes the
        # first characters of the heading off the side mid-sweep.
        if float(f["edge"]) < 0:
            bad.append(f"arc: at {width}px the sweep reaches {f['edge']}px — "
                       f"past the edge of the page, so the heading is clipped "
                       f"while it moves")

        # They cross at the half-way point. Landing on exactly the same
        # spot is two lines of text superimposed, which is a blur.
        if float(f["gap"]) < 4:
            bad.append(f"arc: at {width}px the two phrases pass within "
                       f"{f['gap']}px of each other — at the crossing they are "
                       f"the same height, so this is all that separates them")

        if f["home"] != "true":
            bad.append(f"arc: at {width}px the phrases do not finish in their "
                       f"own places")
    return bad


# The fields drift; they do not look like buttons and they do not move
# with the page.


def check_loops_close(css: str) -> "list[str]":
    """Every lap must close — in position, in size, and in velocity.

    This is the fault that was reported: "we have at some point a
    breaking point". There were two, and only one of them was visible
    in the position.

    A Brownian BRIDGE pins x(T) = x(0) and says nothing about the
    derivative, so looping one still breaks. The paths are periodic
    Fourier sums now, which close in every derivative — and this checks
    the consequence rather than the construction: the change in
    velocity across the seam must be no worse than the largest such
    change anywhere else on the lap. If the seam is the roughest point,
    it is a seam."""
    bad = []
    for name, body in re.findall(r"@keyframes (drop-\d+) \{\n(.*?)\n\}", css, re.S):
        pts = [(float(x), float(y), float(sc)) for x, y, sc in re.findall(
            r"translate\((-?[\d.]+)px, (-?[\d.]+)px\) scale\(([\d.]+)\)", body)]
        if len(pts) < 8:
            bad.append(f"css: `@keyframes {name}` has only {len(pts)} waypoints — "
                       f"too few to follow a curve without cornering")
            continue

        gap = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
        if gap > 0.15:
            bad.append(f"css: `@keyframes {name}` ends {gap:.2f}px from where it "
                       f"began, so the word jumps once a lap")

        # The swell closed at a half cycle for three of six words, which
        # snapped the size back by as much as 24% every lap. Invisible
        # in the position, very visible on the page.
        if abs(pts[-1][2] - pts[0][2]) > 0.002:
            bad.append(f"css: `@keyframes {name}` ends at scale "
                       f"{pts[-1][2]:.3f} having begun at {pts[0][2]:.3f} — the "
                       f"word snaps back to size once a lap. The swell needs a "
                       f"whole number of cycles to the lap")

        n = len(pts) - 1
        seg = [(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1])
               for i in range(n)]
        mean = sum(math.hypot(*v) for v in seg) / n or 1
        jerk = [math.hypot(seg[(i + 1) % n][0] - seg[i][0],
                           seg[(i + 1) % n][1] - seg[i][1]) / mean for i in range(n)]
        if jerk[-1] > max(jerk) * 0.95 and jerk[-1] > 0.2:
            bad.append(f"css: `@keyframes {name}` turns harder at the seam "
                       f"({jerk[-1]:.2f}) than anywhere else on the lap — that "
                       f"is a break, not a drift")
        if max(jerk) > 0.9:
            bad.append(f"css: `@keyframes {name}` changes direction by "
                       f"{max(jerk):.2f} of its own speed in one step. The "
                       f"curve is being sampled too coarsely for its highest "
                       f"mode and the word jerks")
    return bad


def check_cloud_css(css: str) -> "list[str]":
    """No custom property may appear inside the drift keyframes.

    HONEST ABOUT WHAT THIS IS: a structural guard, not a measurement.
    Whether an animation actually runs on the compositor cannot be read
    from JavaScript, and this harness has no way to ask. What it can do
    is hold the shape that makes compositing possible — keyframes whose
    values must be re-resolved from custom properties are computed on
    the main thread, and that is what made the drift land on the pixel
    grid and look stepped on a 1x screen.

    So this fails if the shorter, tempting form comes back. It cannot
    tell you the drift is smooth; it can tell you it is still eligible
    to be."""
    bad = []
    for name, body in re.findall(r"@keyframes (drop-\d+) \{([^}]*(?:\}[^@]*?)*?)\n\}",
                                 css):
        if "var(" in body:
            bad.append(f"css: `@keyframes {name}` uses a custom property. "
                       f"Those keyframes cannot be handed to the compositor, "
                       f"so the drift is computed on the main thread and "
                       f"lands on the pixel grid — which is what made it look "
                       f"stepped on a desktop")
    if not re.search(r"@keyframes drop-1 \{", css):
        bad.append("css: the drift keyframes are gone")
    return bad


def check_cloud(chrome: str, out: Path, url: str, still: bool) -> "list[str]":
    (out / "_cloud.html").write_text(probe("cloud"), encoding="utf-8")
    said = dom(chrome, url + "/_cloud.html", 1000, 900, reduced=still)
    said = only_the_verdict(said)
    found = re.search(r"CLOUD ([^<]*)", said)
    if not found:
        return ["cloud: the probe returned no verdict"]
    where = "with motion stilled" if still else "at rest"
    bad = []
    for word in found.group(1).split():
        width, _, rest = word.partition(":")
        if "=" not in rest:
            bad.append(f"cloud: at {width}px there are no drifting words "
                       f"({rest})")
            continue
        f = dict(kv.split("=") for kv in rest.split(":"))

        if still:
            # Stillness is the whole requirement here; nothing else is
            # different, so nothing else is asserted twice.
            if f["anims"] != "0":
                bad.append(f"cloud: at {width}px the words still drift under "
                           f"reduced motion ({f['anims']} animations)")
            continue

        if f["boxed"] != "0":
            bad.append(f"cloud: at {width}px {f['boxed']} of the words have a "
                       f"border or a fill — that is the capsule that made six "
                       f"unclickable things look like buttons")
        if int(f["fonts"]) < 3:
            bad.append(f"cloud: at {width}px the words are all much of a size "
                       f"({f['fonts']} distinct) — the varying scale is the "
                       f"whole of the effect")
        if f["anims"] == "0":
            bad.append(f"cloud: at {width}px nothing drifts {where}")
        if f["scrolly"] != "0":
            bad.append(f"cloud: at {width}px {f['scrolly']} animations are "
                       f"driven by the scroll. They must keep their own "
                       f"clock — the words move when the page is still, not "
                       f"because it moved")
        if int(f["periods"]) < 4:
            bad.append(f"cloud: at {width}px the drifts share "
                       f"{f['periods']} periods between them, so the words "
                       f"swing in step. That is a metronome, not water")
        if f["over"] != "0":
            bad.append(f"cloud: at {width}px a word leaves the page in "
                       f"{f['over']} of 1200 sampled positions. The page clips "
                       f"rather than scrolls, so that is a word with its end "
                       f"cut off")
        if f["collide"] != "0":
            bad.append(f"cloud: at {width}px two words overlap in "
                       f"{f['collide']} sampled positions — the drift and the "
                       f"swell have outgrown the gap they live in")
        if f.get("held") != "paused":
            bad.append(f"cloud: at {width}px the words keep drifting "
                       f"while the page is being scrolled (play-state "
                       f"{f.get('held')!r}) — they were asked to hold "
                       f"still until it settles")
        if f["layer"] != "yes":
            bad.append(f"cloud: at {width}px the words are not promoted to "
                       f"their own layer, so the drift is snapped to the "
                       f"pixel grid. At these speeds that is a word holding "
                       f"still for seconds and then jumping a whole pixel")
    return bad


# The band crosses; the buttons travel.
#
# Driven in an iframe, which is what makes the second half checkable at
# all: no animation frames run there, so a link that still TRAVELS
# cannot arrive, while one that CROSSES — an instant jump between two
# timers — arrives exactly. The two are told apart by whether the page
# moved, which is as direct as it gets.


def check_crossing(chrome: str, out: Path, url: str, still: bool) -> "list[str]":
    (out / "_cross.html").write_text(probe("cross"), encoding="utf-8")
    # A budget: the probe now makes two more journeys — the hero
    # button and the logo — and the default 3s cut it off mid-way,
    # which reads as "the probe could not run".
    said = dom(chrome, url + "/_cross.html", 500, 900, reduced=still,
               budget=22000)
    said = only_the_verdict(said)
    found = re.search(r"CROSS ([^<]*)", said)
    if not found:
        return ["cross: the probe returned no verdict"]
    verdict = found.group(1).strip()
    if "=" not in verdict:
        return [f"cross: the probe could not run — {verdict}"]
    f = dict(kv.split("=") for kv in verdict.split())
    bad = []

    if f["inert"] != "y":
        bad.append("cross: the veil takes pointer events. It lies over the "
                   "whole page, so that is every click on the site swallowed")
    if f["landed"] != "y":
        bad.append(f"cross: a tap on the band does not put the page at the "
                   f"section ({verdict}). The jump obeys the stylesheet's "
                   f"`scroll-behavior: smooth` unless it is told not to, and "
                   f"a smooth jump outlives the veil that was hiding it")
    if f["held"] != "y":
        bad.append(f"cross: the page does not stay where the band put it "
                   f"({verdict})")
    if f["after"] != "n":
        bad.append(f"cross: the veil is still up after the crossing — the "
                   f"page is left behind a blur ({verdict})")

    if still:
        # Reduced motion: no veil at any point, and the move still works.
        if f["during"] != "n":
            bad.append("cross: the veil is used under reduced motion, which "
                       "is the one setting that asked for none of this")
        return bad

    if f["during"] != "y":
        bad.append(f"cross: the band jumps with nothing over it, so the "
                   f"reader sees the page cut from one place to another "
                   f"({verdict})")
    # EVERY REDIRECTION CROSSES, which is the reverse of what this
    # checked before: the hero button was required NOT to cross, so
    # that the travel it used would be the thing keeping its own
    # motion. The client settled it the other way — one motion for
    # anything that takes the reader somewhere.
    #
    # "It moved" is the evidence, and it is good evidence precisely
    # because the travel could never move anything here: an eased
    # journey needs animation frames, and the probe's iframe runs none.
    if f["btn"] != "y":
        bad.append("cross: the hero button does not cross. Every redirection "
                   "uses the same motion now — and a button that is still "
                   "travelling cannot arrive in this browser at all, which "
                   "is what this reads as 'did not move'")
    if f.get("logo") != "y":
        bad.append("cross: the logo does not cross. From the foot of the page "
                   "it used to rewind the whole height, which is the journey "
                   "the client asked to be rid of")
    if f.get("top") != "y":
        bad.append(f"cross: the logo crossed and the page is not at the top "
                   f"({verdict})")
    return bad


# A document is shown and not served.


def check_document(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_doc.html").write_text(probe("doc"), encoding="utf-8")
    said = dom(chrome, url + "/_doc.html", 500, 900, budget=20000)
    said = only_the_verdict(said)
    found = re.search(r"DOC ([^<]*)", said)
    if not found:
        return ["doc: the probe returned no verdict"]
    verdict = found.group(1).strip()
    if verdict == "none":
        return []                      # no dossier on the page, nothing to check
    if "=" not in verdict:
        return [f"doc: the probe could not run — {verdict}"]
    f = dict(kv.split("=") for kv in verdict.split())
    bad = []

    if int(f["pages"]) < 1:
        bad.append("doc: the document has no pages")
    if f["links"] != "0":
        bad.append(f"doc: there are {f['links']} links inside the document. A "
                   f"dossier is shown, never handed over — nothing in it may "
                   f"point at a file")
    if f["pos"] != "fixed" or f["covers"] != "y":
        bad.append(f"doc: the reading surface is not the page ({verdict}). A "
                   f"transformed or filtered ancestor becomes the containing "
                   f"block for `position: fixed`, and the document ends up in "
                   f"a box inside the card")
    if f["scrolls"] != "y":
        bad.append(f"doc: the pages do not scroll — scroll mode is the whole "
                   f"of what a dossier is ({verdict})")
    if float(f["sharp"]) < 1.8:
        bad.append(f"doc: each page is served at {f['sharp']}x the size it is "
                   f"shown. That is not enough to read on a dense screen")
    if f["onpage"] != "stays":
        bad.append("doc: clicking a page closes the document. A click on a "
                   "page is someone reading it")
    if f["onground"] != "closes":
        bad.append("doc: clicking the margin does not close the document")
    return bad


def check_no_pdf_served(out: Path) -> "list[str]":
    """Nothing in the built site is a PDF, and no page image is served
    at a size the page does not use.

    The promise is narrow and worth keeping exact: a file the browser
    renders is a file the reader already has, so the only honest version
    of "not downloadable" is that the document was never published. This
    is what holds that true."""
    bad = []
    pdfs = [p for p in out.rglob("*") if p.suffix.lower() == ".pdf"]
    if pdfs:
        bad.append(f"doc: the built site serves {pdfs[0].name}. The PDF is "
                   f"meant to stay behind — only its pages are published")

    # The 1600px originals are build inputs, not output. `ignored_content`
    # keeps them out, and ONLY the `**/` form of the glob does — measured.
    originals = list(out.glob("dossier-*.jpg"))
    if originals:
        bad.append(f"doc: {len(originals)} full-size page image(s) are served "
                   f"as well as the derivatives ({originals[0].name}). Check "
                   f"`ignored_content` in config.toml still starts with `**/`")
    return bad


# Cream by default; the work turns the light grey, once, for this visit.
#
# DRIVEN WITH MOTION STILLED, deliberately. The change is eased by a
# 700ms transition, and a transition in an iframe never progresses —
# there are no animation frames — so the computed colour stays at the
# value it started from and every reading says "nothing happened".
# Under reduced motion the page sets the palette without the easing,
# which is the state machine this is here to check. The easing itself
# is a thing to look at, not to assert.


def check_tint(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_tint.html").write_text(probe("tint"), encoding="utf-8")
    said = dom(chrome, url + "/_tint.html", 500, 900, reduced=True, budget=25000)
    said = only_the_verdict(said)
    found = re.search(r"TINT ([^<]*)", said)
    if not found:
        return ["tint: the probe returned no verdict"]
    verdict = found.group(1).strip()
    if "=" not in verdict:
        return [f"tint: the probe could not run — {verdict}"]
    f = dict(kv.split("=") for kv in verdict.split())
    bad = []

    def warm(step: str) -> bool:
        return int(f[step].split(":")[1]) > 6

    def named(step: str) -> str:
        return f[step].split(":")[0]

    if named("arrive") != "none" or not warm("arrive"):
        bad.append(f"tint: the page does not arrive in cream ({verdict}). "
                   f"Every visit starts there, and nothing is remembered")
    if f["scrolled"] != f["arrive"]:
        bad.append(f"tint: scrolling changed the light ({verdict}). A press "
                   f"does that — the hero button or an entry in the menu — "
                   f"and nothing else")
    if named("clicked") != "cool" or warm("clicked"):
        bad.append(f"tint: Explore selected work did not turn the light grey "
                   f"({verdict})")
    if f["again"] != f["clicked"]:
        bad.append(f"tint: clicking it a second time changed something "
                   f"({verdict}). It has already been done")
    if f["returned"] != f["arrive"]:
        bad.append(f"tint: coming back does not start again in cream "
                   f"({verdict}) — something was remembered that should not "
                   f"have been")
    # EVERY entry in the menu, which is the rule the client settled on:
    # the light says "you have left the top of the page", not "you have
    # gone into the work". The first entry in the menu is the one tested
    # — under the old rule it was the control that had to stay cream, so
    # this line failing is exactly how a reverted template would show.
    if named("firstentry") != "cool":
        bad.append(f"tint: the first entry in the menu did not turn the light "
                   f"grey ({verdict}). Every section in the menu does it now, "
                   f"not only Selected Work")
    if f["viamenu"] != f["clicked"]:
        bad.append(f"tint: the last entry in the menu does not do what the "
                   f"hero button does ({verdict}). It should not matter which "
                   f"door was used — and this is also the second visit, so it "
                   f"proves the trigger works again after coming back")
    return bad


# The open patchwork takes the screen, and its photograph fills it.


def check_horizon_ceiling(chrome: str, out: Path, url: str) -> "list[str]":
    """The horizon is measured against the copy that will be ON SCREEN.

    A project's photographs share a height, and that height may not
    exceed the pixels the photograph has. The page reads those pixels
    from `data-big-h` — the copy swapped in when the project opens —
    because at the moment it measures, only the small copy has loaded.

    Read from the loaded image instead, the ceiling is the SMALL copy's
    height and the carousel comes out a fraction of its size. It cannot
    be seen with the stand-ins, whose two copies are identical, so this
    runs against a build where they differ.
    """
    (out / "_patch.html").write_text(probe("patch"), encoding="utf-8")
    said = dom(chrome, url + "/_patch.html", 1450, 950, budget=30000)
    said = only_the_verdict(said)
    found = re.search(r"PATCH ([^<]*)", said)
    if not found:
        return ["horizon: the probe returned no verdict"]
    seen: "dict[str, dict[str, str]]" = {}
    bad = []
    for word in found.group(1).split():
        width, _, rest = word.partition(":")
        if "=" in rest:
            seen.setdefault(width, {}).update(
                dict(kv.split("=") for kv in rest.split(":")))
        else:
            # The probe reached the carousel and threw, or never reached
            # it. Either way there is nothing to compare, and this used
            # to `continue` past it — so renaming the carousel out of the
            # page left this check, whose entire subject is that
            # carousel, reporting success.
            bad.append(f"horizon: at {width}px the probe could not run — "
                       f"{rest or 'it wrote no reading for this width'}")

    # NOTHING MEASURED IS NOT A PASS. Both loops below are over what the
    # probe found, and a verdict that carries no widths at all ran none
    # of them.
    measured = [f for f in seen.values() if "heights" in f and "owed" in f]
    if not measured:
        return bad + ["horizon: the probe measured no carousel at any width, "
                      "so the ceiling was never compared with the arithmetic"]

    for width, f in seen.items():
        if "heights" not in f or "owed" not in f:
            continue
        tall = int(f["heights"].split(",")[0])
        if abs(tall - int(f["owed"])) > 2:
            bad.append(
                f"horizon: at {width}px, with a strip copy smaller than the "
                f"one that opens, the photographs are {tall}px tall where "
                f"the arithmetic says {f['owed']}px. The ceiling is being "
                f"read from whatever has loaded rather than from the copy "
                f"that will be on screen")
    return bad


def check_two_faces(chrome: str, out: Path, url: str) -> "list[str]":
    """A headline set in two typefaces still plays word by word.

    The splitter refused any heading containing an element, so the
    first version of this feature would have bought the designer two
    faces at the cost of the headline's entrance — on the display
    lines, which is exactly where both live. It reads runs now.

    Run against a build whose headline is marked up, because nothing in
    the real content uses the markers yet: the request was to leave the
    room, not to fill it.
    """
    (out / "_faces.html").write_text(probe("faces"), encoding="utf-8")
    said = dom(chrome, url + "/_faces.html", 900, 900, budget=20000)
    said = only_the_verdict(said)
    found = re.search(r"FACES ([^<]*)", said)
    if not found:
        return ["faces: the probe returned no verdict"]
    verdict = found.group(1).strip()
    if "=" not in verdict:
        return [f"faces: the probe could not run — {verdict}"]
    f = dict(kv.split("=", 1) for kv in verdict.split())

    bad = []
    if f["split"] != "y":
        bad.append(
            "faces: a headline carrying a second typeface was not split into "
            "words at all, so it has lost its entrance — which is the trade "
            "this was written to avoid")
    if int(f["boxes"]) < 2:
        bad.append(f"faces: {f['boxes']} word box(es) in the headline, so "
                   f"nothing was taken apart")
    if int(f["faces"]) < 1:
        bad.append(
            "faces: the second typeface did not survive being split into "
            "words — the span the template inserted is gone, so the "
            "headline is back to one face")
    if f.get("holders") != "1":
        bad.append(
            f"faces: the marked word spans {f.get('holders')} boxes. A word "
            f"is one box however many faces it is set in, or a line can "
            f"break inside it")

    # And it still reads as what was written.
    import urllib.parse
    text = urllib.parse.unquote(f.get("text", ""))
    if "((" in text or "))" in text:
        bad.append(f"faces: the markers are still in the page ({text!r}) — a "
                   f"reader is being shown the notation instead of the "
                   f"typeface")
    if not text.endswith("."):
        bad.append(f"faces: the headline no longer ends as it was written "
                   f"({text!r}), so something was lost in the splitting")
    return bad


def check_lost(chrome: str, out: Path, url: str) -> "list[str]":
    """A photograph that fails leaves ground, not a torn page.

    Reported from the deployed site on a phone: torn-page icons on a
    cold landing. Measured in a browser, the two states are nothing
    alike — an image still LOADING draws nothing at all, while an image
    that FAILED draws the glyph and the whole of its `alt`, and 163 of
    this page's images carry a sentence there.

    Every file the live site serves answers correctly, so nothing is
    missing; what fails is the landing, where the document asks for 167
    images while the warming queue asks for the rest. So the page asks
    again, twice, and only then puts a clear pixel in the box.
    """
    (out / "_lost.html").write_text(probe("lost"), encoding="utf-8")
    said = dom(chrome, url + "/_lost.html", 500, 900, budget=20000)
    said = only_the_verdict(said)
    found = re.search(r"LOST ([^<]*)", said)
    if not found:
        return ["lost: the probe returned no verdict"]
    verdict = found.group(1).strip()
    if "=" not in verdict:
        return [f"lost: the probe could not run — {verdict}"]
    f = dict(kv.split("=") for kv in verdict.split())

    bad = []
    if int(f["asked"]) < 2:
        bad.append(
            f"lost: a photograph that failed was asked for {f['asked']} "
            f"time(s). A request dropped in the crowd of a cold landing "
            f"clears on the second ask, and nothing else on the page ever "
            f"asks again")
    if f["lost"] != "y":
        bad.append(
            "lost: a photograph that failed every time is not marked, so "
            "the browser is left drawing its own broken-image glyph and the "
            "whole alt sentence beside it")
    if f["content"] != "replaced":
        bad.append(
            f"lost: the failed photograph still draws its own content "
            f"({verdict}). `content: url()` with a real file is what "
            f"removes the glyph — `color: transparent` removes the words "
            f"and leaves the torn page, which was measured")
    if f["ground"] != "yes":
        bad.append(
            "lost: the failed photograph has no ground behind it, so it is "
            "a hole in the page rather than a quiet panel")
    return bad


def check_toolbar(chrome: str, out: Path, url: str) -> "list[str]":
    """The open patchwork follows the screen it is on.

    To the page, the browser toolbar arriving is the visible viewport
    getting shorter — so this opens the patchwork and changes the height
    around it, both before and after the tap.

    WHAT IT CANNOT SEE, twice over.

    First, iOS does not shrink the layout viewport when its toolbar
    appears; it draws the toolbar over it, and headless Chrome has no
    toolbar at all. The original fault — a patchwork opened while the
    toolbar was showing and left at the wrong size, because an open
    front cannot be scrolled and nothing prompted a relayout — is
    invisible here and was verified on a phone.

    Second, and worth knowing before trusting this: inside an iframe
    there is no browser chrome, so `svh`, `lvh` and `dvh` all resolve to
    the same number. This check CANNOT tell which unit the stylesheet
    uses — and the difference between them is the whole of the bug it
    is named after. `dvh` made the photograph shrink away from the
    toolbar; `lvh` keeps it the size of the screen and lets the toolbar
    draw over it. An invariant holds the unit, because this cannot.

    What this does hold is the precondition for either: the
    photograph's height follows the box it is in rather than being
    frozen at whatever the screen was when the front opened.
    """
    (out / "_toolbar.html").write_text(probe("toolbar"), encoding="utf-8")
    said = dom(chrome, url + "/_toolbar.html", 500, 1000, budget=30000)
    said = only_the_verdict(said)
    found = re.search(r"TOOLBAR ([^<]*)", said)
    if not found:
        return ["toolbar: the probe returned no verdict"]

    bad = []
    seen = 0
    told = set()
    for word in found.group(1).split():
        label, _, rest = word.partition(":")
        told.add(label)
        if "=" not in rest:
            bad.append(f"toolbar: the {label} run could not complete — "
                       f"{rest or 'it wrote no reading'}")
            continue
        f = dict(kv.split("=") for kv in rest.split(":"))
        seen += 1

        # ---- the carousel, one level in ---------------------------
        # Nobody had checked this one: it is the same fixed full-screen
        # box as the patchwork, and it was left on `inset: 0` purely
        # because it had not been seen to misbehave.
        if label == "carousel":
            if not (99 <= int(f["boxtall"]) <= 101):
                bad.append(
                    f"toolbar: after the screen changed, the open carousel's "
                    f"box is {f['boxtall']}% of its height ({f['box']} on a "
                    f"{f['screen']} screen) — it is keeping the screen it "
                    f"opened with")
            if f["fits"] != "y":
                bad.append(
                    f"toolbar: after the screen changed, the carousel's "
                    f"photograph is {f['photo']}px tall on a {f['screen']} "
                    f"screen — taller than the screen, so part of the "
                    f"photograph someone opened to look at is off it")
            if int(f["band"]) < 42:
                bad.append(
                    f"toolbar: after the screen changed, there is "
                    f"{f['band']}px of ground above or below the carousel's "
                    f"photograph. That ground is the way back out at this "
                    f"level, and a shorter screen must not eat it")
            if f["sizes"] != "1":
                bad.append(
                    f"toolbar: after the screen changed, the carousel's "
                    f"photographs are no longer one height "
                    f"({f['sizes']} different) — swiping would jump")
            continue
        # MATCHES THE SCREEN, not merely covers it. A frozen box is
        # wrong in both directions and which one you get depends on
        # which way the viewport moved: too short leaves ground at the
        # bottom, which is how this was reported, and too tall pushes
        # the way-out band off the screen entirely. `>= 99` passed a
        # box 110% of the screen's height, so it is a range.
        tall, wide = int(f["tall"]), int(f["wide"])
        if not (99 <= tall <= 101) or not (99 <= wide <= 101):
            bad.append(
                f"toolbar: with the viewport changed {label.replace('-', ' ')} "
                f"the tap, the open patchwork is {wide}% wide and {tall}% tall "
                f"on a {f['screen']} screen (photograph {f['photo']}, box "
                f"{f['front']}). It is not following the screen, so on a phone "
                f"it keeps whatever the screen was when it opened — the fault "
                f"this exists for, reported as 'not full screen, and it stays "
                f"short until I close and reopen it'")
    # EVERY RUN REPORTS, or the silence is the finding. A run that
    # simply never appears in the verdict leaves its assertions
    # unexecuted and the check still green.
    missing = {"arrives-after", "already-there", "carousel"} - told
    if missing:
        bad.append(
            f"toolbar: {', '.join(sorted(missing))} wrote no reading at all, "
            f"so nothing was measured for it")
    if seen == 0 and not bad:
        return ["toolbar: the probe measured nothing at any order"]
    return bad


def check_patchwork(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_patch.html").write_text(probe("patch"), encoding="utf-8")
    said = dom(chrome, url + "/_patch.html", 2450, 2050, budget=40000)
    said = only_the_verdict(said)
    found = re.search(r"PATCH ([^<]*)", said)
    if not found:
        return ["patch: the probe returned no verdict"]
    bad = []
    # Two readings per width now — the open patchwork, and the main
    # picture one level further in — each written as `WIDTH:key=value…`.
    # Merged by width so the assertions below can be read as one set.
    seen: "dict[str, dict[str, str]]" = {}
    for word in found.group(1).split():
        width, _, rest = word.partition(":")
        if "=" not in rest:
            bad.append(f"patch: at {width}px the probe could not run — {rest}")
            continue
        seen.setdefault(width, {}).update(
            dict(kv.split("=") for kv in rest.split(":")))

    for width, f in seen.items():

        # 80% of each side. A 3:2 box in a 390x720 screen manages 32% of
        # the height — measured, before it was told to take the screen's
        # own shape — so this is the assertion that tells the two apart.
        # FULL BLEED, both surfaces. It was ">= 80%" when a gutter held
        # the arrangement off the edges and a cap held it to 1600px on a
        # wide monitor; the client asked for edge to edge, so 99 rather
        # than 80 — a point of slack for a fractional device pixel, and
        # nothing like enough to let a gutter back in.
        if int(f["wide"]) < 99 or int(f["tall"]) < 99:
            bad.append(f"patch: at {width}px the open patchwork is "
                       f"{f['wide']}% wide and {f['tall']}% tall. It is meant "
                       f"to take the screen, at the screen's own shape")
        # The support's pixel count is NOT asserted here any more. The
        # big copy no longer upscales — `op="fit"` inside a 2000px box
        # leaves a smaller photograph alone — so what this number
        # reports is the SOURCE's size, and the fixture's stand-ins are
        # 1000px wide. Whether a photograph is big enough to fill a
        # screen is a question about the content, and
        # `tools/content-check.py` asks it where the rest of the launch
        # gate lives. What still belongs here is that the swap happened
        # at all, below.
        # FULL BLEED MEANS NO FRAME EITHER. The hairline every picture
        # on the page carries is right on the card, where this
        # photograph is the ground of an arrangement and one picture
        # among several. At the front it is the screen, and the same
        # 1px traces all four edges of the phone — which is not a
        # photograph filling the screen, it is a photograph with a
        # border around the screen. The card's edge is unchanged and
        # still checked by check_edges.
        if f.get("ground") not in (None, "0"):
            bad.append(
                f"patch: at {width}px the open patchwork's background "
                f"photograph has a {f['ground']}px edge. At full bleed that "
                f"line runs along all four edges of the screen — the prints "
                f"on top keep theirs, the ground it is lying on must not")
        # NOTHING IS SEEN THROUGH THE FRONT. `rgba(…,0)` means a
        # transparent ground, and the layer behind the photograph is
        # deliberately 38% see-through — it is a blur, that is the
        # point. So any strip the photograph does not cover shows the
        # page itself, which is what the reader saw while the toolbar
        # slid in and the fixed box had not caught up. iOS moves fixed
        # elements during that animation and no stylesheet prevents it;
        # what a stylesheet can do is make the worst case a band of
        # ground instead of a view of the page.
        if f.get("behind") != "opaque":
            bad.append(
                f"patch: at {width}px the open patchwork has nothing opaque "
                f"behind the photograph ({f.get('behind')}). The blurred "
                f"layer is "
                f"see-through by design, so any strip the photograph does "
                f"not cover becomes a window onto the page underneath")
        if f.get("waiting") != "n":
            bad.append(
                f"patch: at {width}px the open patchwork still carries "
                f"data-big, so the swap has not happened — the small copy is "
                f"what is on screen")
        # ---- and the pictures, one level in ------------------------
        if "slides" in f:
            if "," in f["slides"]:
                bad.append(
                    f"patch: at {width}px the carousel's slides are not the "
                    f"same size ({f['slides']} across {f['shapes']} "
                    f"photographs). On a wide screen the height bound them "
                    f"all to one horizon; on a phone the width bound them "
                    f"instead and an upright photograph came out twice the "
                    f"height of a landscape one, so swiping jumped")
            if int(f["band"]) < 42:
                bad.append(
                    f"patch: at {width}px there is {f['band']}px of ground "
                    f"above or below the nearest photograph. That ground is the way back at "
                    f"this level — 44px of it, and a ring cannot be used here "
                    f"because it would swallow the swipe to the next "
                    f"photograph")
            if f["enlarged"] != "n":
                bad.append(
                    f"patch: at {width}px a photograph is drawn larger than "
                    f"the pixels it has ({f['slides']} slides). As large as "
                    f"the slide allows, never larger than itself")
            if int(f["of"]) < 97 and f["atpixels"] != "y":
                bad.append(
                    f"patch: at {width}px the widest photograph takes "
                    f"{f['of']}% of the screen and is not at its own pixels "
                    f"either — so it is neither as large as it could be nor "
                    f"as large as it is")
            if int(f["offcentre"]) > 2:
                bad.append(
                    f"patch: at {width}px the first photograph sits "
                    f"{f['offcentre']}px off centre. A carousel opens on one "
                    f"picture in the middle of the screen — and when the snap "
                    f"alignment was on the photograph instead of the slide it "
                    f"settled hard against the left edge with the ground all "
                    f"on one side")
            if int(f["restsat"]) != 0:
                bad.append(
                    f"patch: at {width}px a freshly opened carousel is "
                    f"already scrolled to {f['restsat']}px rather than resting "
                    f"at its start")
            if abs(int(f["heights"].split(",")[0]) - int(f["owed"])) > 2:
                bad.append(
                    f"patch: at {width}px the photographs are "
                    f"{f['heights']}px tall where the arithmetic says "
                    f"{f['owed']}px — as tall as they can all be while the "
                    f"widest still fits, and never past the big copy's own "
                    f"pixels. Reading the ceiling off whatever has loaded "
                    f"gives the SMALL copy's height and a carousel a third "
                    f"of the size it should be")
            if "," in f["heights"]:
                bad.append(
                    f"patch: at {width}px a project's photographs are "
                    f"{f['heights']}px tall — different sizes in the same "
                    f"carousel. They share a horizon: the tallest they can "
                    f"all be while the widest of them still fits. On a wide "
                    f"screen the slide's own height does that by itself, "
                    f"which is why this only ever showed on a phone")
            if f["mounted"] != "y":
                bad.append(
                    f"patch: at {width}px an open photograph has no white "
                    f"mount. A carousel opened from one of the prints had "
                    f"one and a carousel opened from the photograph behind "
                    f"them did not — the prints were passing theirs on by "
                    f"accident, to the carousels inside their own slots")
            if f["framed"] != "y":
                bad.append(
                    f"patch: at {width}px an open photograph has no hairline "
                    f"on it. Every picture carries the same edge — and here "
                    f"it has to be on the PHOTOGRAPH, not on the slide, or "
                    f"it is a rectangle floating around a picture that does "
                    f"not fill it")

        if f["fills"] != "y":
            bad.append(f"patch: at {width}px the photograph behind the prints "
                       f"does not fill the patchwork ({f['img']} inside it). "
                       f"At the front a <summary> sits between the slot and "
                       f"the image, and a percentage height dies on it")
    return bad


def check_form_words(html: str, where: str) -> "list[str]":
    """The form's messages survive the journey into the page.

    They travel as JSON inside an HTML attribute, and they are the
    client's prose — so sooner or later one of them will contain a
    quote, an apostrophe or an ampersand.

    They used to be pasted into the JSON by hand:

        data-says='{"err_mail_missing":"{{ e.err_mail_missing }}", ...}'

    One double quote in any single message broke the whole object.
    `contact.ts` catches the parse failure and falls back to `{}`, so
    EVERY message on the form then showed as its own key —
    "err_mail_missing" where a sentence should be. The page built, and
    content, objects, fr, contact and render all passed in silence.
    Measured, with a quote in one message.
    """
    found = re.search(r"data-says='([^']*)'", html) \
        or re.search(r'data-says="([^"]*)"', html)
    if not found:
        return [f"{where}: the form carries no words at all"]

    raw = html_module.unescape(found.group(1))
    try:
        words = json.loads(raw)
    except ValueError as broken:
        return [f"{where}: the form's messages are not valid JSON "
                f"({broken}). Every one of them will show as its key "
                f"instead of its sentence, and nothing else will say so"]

    # The keys `contact.ts` asks for by name. A missing one shows as the
    # key; an extra one is harmless but means the two have drifted.
    wanted = {"form_sending", "form_sent", "form_failed", "form_offline",
              "err_mail_missing", "err_mail_invalid", "err_mail_long",
              "err_mail_one", "err_subject", "err_message_missing",
              "err_message_long", "err_message_bad", "err_message_links"}
    missing = sorted(wanted - set(words))
    if missing:
        return [f"{where}: the form has no words for {', '.join(missing)} — "
                f"the reader would be shown the key instead"]
    empty = sorted(k for k, v in words.items() if not str(v).strip())
    if empty:
        return [f"{where}: {', '.join(empty)} is empty, which reads as "
                f"nothing happening at all"]
    return []


# Nothing above a fixed element may steal the viewport from it.
#
# `transform`, `filter`, `backdrop-filter`, `perspective`,
# `contain: paint` and `will-change: transform` each make an element the
# containing block for every `position: fixed` thing inside it. The
# fixed thing then sits inside that box instead of the screen, which is
# never what anyone meant by fixed.
#
# This page has been caught by it three times: a header's
# backdrop-filter, a rotated print, and the reveal's own transform
# holding the dossier at 343x757 in the corner of a card. Each was found
# by hand, after the fact. This asks the browser about every fixed
# element at once.


def check_fixed(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_fixed.html").write_text(probe("fixed"), encoding="utf-8")
    said = dom(chrome, url + "/_fixed.html", 500, 900, budget=22000)
    said = only_the_verdict(said)
    found = re.search(r"FIXED ([^<]*)", said)
    if not found:
        return ["fixed: the probe returned no verdict"]
    verdict = found.group(1).strip()
    if "=" not in verdict:
        return [f"fixed: the probe could not run — {verdict}"]
    f = dict(kv.split("=", 1) for kv in verdict.split())

    bad = []
    if int(f["seen"]) < 3:
        bad.append(f"fixed: only {f['seen']} fixed element(s) found. The "
                   f"overlays are fixed when open, so the probe is not "
                   f"opening them and is checking almost nothing")
    if f["caught"] != "none":
        bad.append(f"fixed: {f['caught']} — an ancestor is the containing "
                   f"block, so this is not fixed to the screen but to a box "
                   f"inside the page. Look for a transform, a filter, a "
                   f"backdrop-filter or a will-change above it")
    return bad


def check_shape(html: str, where: str) -> "list[str]":
    """The two buttons that open the form look like the form.

    They must not read as the same action as "Explore selected work",
    which moves down the page. The difference is the outline, so this
    asserts the class that carries it — on both, and on nothing else.

    A count, not a presence: the fault worth catching is the shape
    falling off ONE of the two, which a presence check sees as fine."""
    bad = []

    # Every opener of the form, by the attribute that makes it one.
    openers = re.findall(r'<a [^>]*data-talk[^>]*>', html)

    # The CLASS attribute, not the tag. `data-talk` contains "talk" too,
    # so a substring test over the whole tag calls every opener shaped —
    # it passed a mutation only because the minifier happened to put the
    # attributes in an order where it still broke.
    def classes(tag: str) -> "list[str]":
        found = re.search(r'class="([^"]*)"|class=([^\s>]+)', tag)
        return (found.group(1) or found.group(2)).split() if found else []

    shaped = [a for a in openers if "bubble" in classes(a)]
    if len(openers) != 2:
        bad.append(f"{where}: {len(openers)} buttons open the form, expected 2 "
                   "(the hero and the foot of Contact)")
    if len(shaped) != len(openers):
        bad.append(f"{where}: {len(openers) - len(shaped)} of the form's "
                   "buttons has lost its shape — the two must match")

    # And the shape is not on anything that is not an opener. A page
    # where every button is a speech bubble has no distinction left.
    elsewhere = len(TALK_BTN.findall(html)) - len(shaped)
    if elsewhere > 0:
        bad.append(f"{where}: {elsewhere} button(s) wear the form's shape "
                   "without opening the form")

    return bad


def check_shape_css(css: str) -> "list[str]":
    """The shape is a shape, and the press is untouched.

    `.btn.talk` may change the outline. What it must not do is restate
    `transform` or `transition`, which is where the press and the
    release live — the brief was explicit that the press survives and
    only the shape changes. A `transform` on the rule itself would
    compete with `:active`; one on `::after` only moves the ellipsis."""
    bad = []

    rule = re.search(r"\.btn\.bubble\s*\{([^}]*)\}", css)
    if rule is None:
        return ["css: `.btn.bubble` is gone — the two buttons have no shape"]
    body = rule.group(1)
    if "border-radius" not in body:
        bad.append("css: `.btn.bubble` no longer changes the outline")
    for forbidden in ("transform", "transition", "animation"):
        if forbidden in body:
            bad.append(f"css: `.btn.bubble` sets `{forbidden}`, which is what "
                       "the press is made of — the shape may change, the "
                       "press may not")

    # The press on a hovering device must be written for the HOVERED
    # button. Without these the desktop press flashes the outline button
    # from near-white to the dark ground and back — measured.
    for sel in (".btn:not(.primary):hover:active", ".btn.primary:hover:active"):
        if sel not in css:
            bad.append(f"css: `{sel}` is gone. On a desktop the pointer is "
                       "always hovering when it presses, so without it the "
                       "press is written for a state that never happens there")

    after = re.search(r"\.btn\.bubble::after\s*\{([^}]*)\}", css)
    if after is None:
        bad.append("css: the ellipsis is gone")
    elif after.group(1).count("content") < 2:
        bad.append("css: the ellipsis has only one `content` declaration. "
                   "The alternative-text form is dropped whole by browsers "
                   "that do not know it, so the plain one must come first")

    return bad


GROUP = re.compile(r'<details[^>]*\bclass=["\']?group[\s"\'>]')
SHOTS = re.compile(r'\bclass=["\']?shots ')
SLOT = {k: re.compile(rf'\bslot-{k}[\s"\'>]') for k in range(1, 6)}
LAZY = re.compile(r'\bloading=["\']?lazy')
LOOK = re.compile(r'class=["\']?look[\s"\'>]')
IN_CHIP = re.compile(r'patch-count[^>]*>\s*<i')


def check_gallery(html: str) -> "list[str]":
    """The three levels are all there, and the right way round."""
    bad = []

    if len(GROUP.findall(html)) != 1:
        bad.append(f"gallery: one reference has projects, "
                   f"{len(GROUP.findall(html))} fridges rendered")

    # Five projects, so five prints on the fridge — and each appears
    # twice, once on the card and once at the front.
    for k in range(1, 6):
        many = len(SLOT[k].findall(html))
        if many != 2:
            bad.append(f"gallery: slot {k} appears {many} time(s); it belongs "
                       "on the card and again at the front")

    # The light that says there is more inside. One per fridge, and
    # OUT of the count chip: at 9px inside a label it read as
    # punctuation and had to be pointed out, which is the opposite of
    # what it is for.
    # ONE PER PRINT IN THE FOCUS, not one on the card. The card is one
    # photograph and obviously a thing to tap; the focus is five of
    # them and nothing there said that each one opens in turn.
    lights = len(LOOK.findall(html))
    if lights != 5:
        bad.append(f"gallery: 5 projects in the focus, {lights} light(s) "
                   "inviting a tap")
    if re.search(r'<figure class=["\']?patch["\']?>(?:(?!</figure>).)*class=["\']?look', html, re.S):
        bad.append("gallery: the light is back on the card, where the next "
                   "move is already obvious — it belongs in the focus")
    if IN_CHIP.search(html):
        bad.append("gallery: the light is back inside the count chip, where "
                   "it reads as punctuation rather than as an invitation")

    shots = len(SHOTS.findall(html))
    if shots != 5:
        bad.append(f"gallery: 5 projects, {shots} of them open a carousel")

    # THE BIG ONE IS NOT LAZY, and the carousel is.
    #
    # Six photographs — one per reference, what the page carried before
    # the gallery — so the cover waits for them exactly as it used to.
    # Made lazy with the rest, four of six had not arrived by the time a
    # phone reached them: a dark panel with prints floating on nothing.
    ground = re.search(r'<li class=["\']?slot-1["\']?>\s*<img[^>]*>', html)
    if not ground:
        bad.append("gallery: the fridge has no photograph underneath it")
    elif LAZY.search(ground.group(0)):
        bad.append("gallery: a reference's photograph is lazy, so the card "
                   "can be reached before it arrives")

    for shot in ("Probe photograph one", "Probe photograph two",
                 "Probe photograph three"):
        # EVERY occurrence, not the first. A project's first photograph
        # is also its cover, and the cover is eager on purpose — so
        # searching for one tag found the cover and called the carousel
        # eager. The carousel copy is the one that must be lazy.
        tags = re.findall(r"<img[^>]*" + re.escape(shot) + r"[^>]*>", html)
        if not tags:
            bad.append(f"gallery: {shot!r} is on no page")
        elif not any(LAZY.search(t) for t in tags):
            bad.append(f"gallery: {shot!r} is eager everywhere it appears, "
                       "so the card waits for the whole carousel")

    return bad


# Closing a group must put its projects back.
#
# <details> remembers. Open a project's carousel, close the group around
# it, and the project stays open — so the next visit to that reference
# lands straight in the carousel, past the patchwork the reader was
# going back for.
#
# This one IS drivable here: it needs no clicks and no animation frames,
# only `details.open`. The waits are because `toggle` is fired
# asynchronously — reading straight after setting it reports the state
# before the handler has run, which is how this check first told me the
# fix had not worked.


def check_reopen(chrome: str, out: Path, url: str) -> "list[str]":
    page = (out / "index.html").read_text(encoding="utf-8")
    css = re.search(r'<link[^>]*site\.css[^>]*>', page)
    js = re.search(r'<script[^>]*landing\.js[^>]*></script>', page)
    sec = re.search(r'<section id="?work"?.*?</section>', page, re.S)
    if not (css and js and sec):
        return ["reopen: could not assemble the probe page"]
    (out / "_reopen.html").write_text(
        '<!doctype html><html lang=en class=js><meta charset=utf-8>'
        + css.group(0) + '<body><p id=verdict>no verdict</p><main>'
        + sec.group(0) + '</main>' + js.group(0) + probe("reopen") + '</html>',
        encoding="utf-8")
    said = dom(chrome, url + "/_reopen.html", 500, 900)
    said = only_the_verdict(said)
    found = re.search(r"RESULT ([^<]*)", said)
    if not found:
        return ["reopen: the probe returned no verdict"]
    verdict = found.group(1).strip()
    bad = []
    if "both=true" not in verdict:
        bad.append(f"reopen: the two levels did not both open ({verdict})")
    if "left=false" not in verdict:
        bad.append("reopen: closing a group leaves its project open, so going "
                   "back in lands straight in the carousel")
    if "reopened=false" not in verdict:
        bad.append("reopen: a reference reopens into the carousel rather than "
                   "its patchwork")
    # One level at a time: the ground under a carousel closes the
    # carousel and leaves the group it came from standing.
    if "carousel=false group=true" not in verdict:
        bad.append("ground: clicking beside a photograph does not close the "
                   f"carousel back to its group ({verdict})")
    if "afterFront=false" not in verdict:
        bad.append("ground: clicking beside the group does not close it")
    # The control first: a strip that could not be scrolled proves
    # nothing about where it reopens.
    if "wandered=true" not in verdict:
        bad.append(f"reopen: the probe could not scroll the strip, so what it "
                   f"says about coming back means nothing ({verdict})")
    elif "backAtStart=true" not in verdict:
        bad.append(f"reopen: a project left on its third photograph opens on "
                   f"the third next time ({verdict}). The <details> is put "
                   f"back when its group closes; the scroll inside it has to "
                   f"be as well, or coming back to a reference lands "
                   f"mid-strip")
    return bad


# The cover is never a flicker.
#
# On a fast connection the page was ready before anyone had seen the
# cover, and the fade began the instant it appeared — which reads as a
# flash of something rather than as a page arriving. Measured from
# inside a frame, because the cover's whole life is over before an
# ordinary screenshot could catch it: 28ms without the floor, 443ms
# with it.


def check_cover(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_cover.html").write_text(probe("cover"), encoding="utf-8")
    # LONGER THAN THE PROBE'S OWN FAILSAFE. The probe gives up watching
    # after 8s and says what it saw; the default budget here was 3s, so
    # the clock stopped first and both diagnoses below — "never-covered"
    # and "never-uncovered" — were unreachable. Renaming `booting` out
    # of the page proved it: the cover was gone and this reported "the
    # probe returned no verdict", which is the one message that means
    # "ask again", not "the page is broken".
    said = dom(chrome, url + "/_cover.html", 500, 900, budget=12000)
    said = only_the_verdict(said)
    found = re.search(r"COVERED-FOR ([a-z0-9-]+)", said)
    if not found:
        return ["cover: the probe returned no verdict"]
    verdict = found.group(1)

    # NO LONGER A STOPWATCH.
    #
    # This asserted the cover was up for between 380ms and 2000ms, and
    # it failed twice on a page that was behaving perfectly — 41ms on
    # one run, 5026ms on another, each passing on the next try. A
    # virtual clock on a loaded machine cannot be asked how long
    # something took, and a check that fails at random is worse than
    # none: it gets explained away, and then ignored.
    #
    # What a browser CAN say is whether the cover appeared and whether
    # it left, which is what is asked here. How long it must stay is
    # arithmetic, and `tools/cover-check.mjs` answers that exactly.
    if verdict == "never-covered":
        return ["cover: the page was never behind it. Nothing holds the "
                "reader back from a half-built page"]
    if verdict == "never-uncovered":
        return ["cover: it never left — the page is stuck behind it"]
    if not verdict.isdigit():
        return [f"cover: {verdict}"]
    return []


# No light is hidden under the print next to it.
#
# The prints overlap and a later one paints over an earlier one. I first
# worked this out from the arrangement rectangles and got it wrong: a
# rotated print reaches about 4.4% past its box at 6deg and I had
# allowed 2%, so one light shipped underneath its neighbour.
#
# This asks the BROWSER instead — `elementFromPoint` at five places on
# each light, and a light is hidden only if what comes back belongs to a
# print painted AFTER it. The ground beneath is fine; the print on top
# is not. Hit testing accounts for rotation, outlines and stacking
# without any of it being modelled here.


def check_takes_turns(css: str) -> "list[str]":
    """One light at a time, which is what the fifth attempt is.

    Five lights pulsing in step read as five notifications on someone's
    photographs. They take turns now, by nothing more than a delay per
    slot — so the failure to guard against is not a broken animation
    but a copy-paste: five slots, five identical delays, and the page
    is quietly back to what the client did not like, with every check
    still green.
    """
    delays = re.findall(r"\.shots\.slot-(\d)\s*\{\s*--look-delay:\s*([0-9.]+)s", css)
    if len(delays) < 5:
        return [f"turns: {len(delays)} of the five print slots give their "
                f"light a delay; without one they light together"]
    spread = {d for _slot, d in delays}
    if len(spread) != len(delays):
        return [f"turns: the slots share a delay ({', '.join(sorted(spread))}) "
                f"— their lights come on together, which is the thing being "
                f"fixed"]
    if "infinite both" not in css or "animation: turn" not in css:
        return ["turns: the light no longer takes a turn at all — the "
                "animation that brings it in and out is gone"]
    return []


def check_unspent(chrome: str, out: Path, url: str) -> "list[str]":
    """Motion nobody has reached yet is still waiting for them.

    THE BUG THIS IS FOR. The failsafe that guarantees nothing stays
    invisible used to add `in` to every `.split` and every `.reveal` on
    the page at 7s, wherever they were. The page is 9000px, so every
    reader arrived at a heading whose motion had already been spent off
    screen: nothing to transition, the words simply in place. Scrolling
    away and back played it — leaving is a real intersection change, so
    the class came off — which is how it was reported: "Formats in
    development does not animate on the first land; you have to go up
    and down to trigger it".

    So this loads the page, leaves it exactly where it opens, waits past
    the failsafe, and asks whether a heading at the BOTTOM of the page
    has been released. Nothing about animation timing is asserted — that
    is flaky under a virtual clock and deliberately left alone (see
    check() above) — only that something thousands of pixels away has
    not been marked as arrived.
    """
    waits = re.search(r"MOTION_FAILSAFE_MS = (\d+)",
                      (ROOT / "src" / "motion.ts").read_text(encoding="utf-8"))
    if not waits:
        return ["unspent: src/motion.ts no longer names MOTION_FAILSAFE_MS, so "
                "this check cannot know how long to wait"]
    budget = int(waits.group(1)) + 5000

    said = dom(chrome, url, 390, 720, budget=budget)

    # The last display headline in the document, whatever it is called:
    # the bottom of the page is the one place a 720px viewport certainly
    # has not been.
    last = None
    for m in re.finditer(r"<h2\b[^>]*>", said):
        found = re.search(r'class=(?:"([^"]*)"|([^\s>]+))', m.group(0))
        if found and "split" in (found.group(1) or found.group(2) or ""):
            last = found.group(1) or found.group(2)
    if last is None:
        return ["unspent: no split headline in the page at all, so nothing "
                "here measured anything — the words are not being split, or "
                "the script did not run"]

    if re.search(r"\bin\b", last):
        marked = len(re.findall(r'class="[^"]*\bin\b', said)) \
            + len(re.findall(r"class=in\b", said))
        return [
            f"unspent: the last headline on the page is already released "
            f"({last!r}) with the page never scrolled, {int(waits.group(1))}ms "
            f"after it loaded — {marked} block(s) marked as arrived. Its "
            f"motion has been spent where nobody could see it, so the reader "
            f"who scrolls down to it will see nothing move, and will only get "
            f"it by scrolling away and coming back"
        ]
    return []


def check_lights(chrome: str, out: Path, url: str) -> "list[str]":
    page = (out / "index.html").read_text(encoding="utf-8")
    css = re.search(r'<link[^>]*site\.css[^>]*>', page)
    sec = re.search(r'<section id="?work"?.*?</section>', page, re.S)
    if not (css and sec):
        return ["lights: could not assemble the probe page"]
    (out / "_lights.html").write_text(
        '<!doctype html><html lang=en class=js><meta charset=utf-8>'
        + css.group(0) + '<body><p id=out>?</p><main>' + sec.group(0)
        + '</main>' + probe("light") + '</html>', encoding="utf-8")
    said = dom(chrome, url + "/_lights.html", 1100, 1000)
    said = only_the_verdict(said)
    found = re.search(r"LIGHTS seen=(\d+) hidden=([^<]*)", said)
    if not found:
        return ["lights: the probe returned no verdict"]
    seen, hidden = int(found.group(1)), found.group(2).strip()
    bad = []
    if seen == 0:
        bad.append("lights: none found — the invitation to tap is missing")
    if hidden != "none":
        bad.append(f"lights: hidden under the print beside them — {hidden}")
    return bad


def check_live(html: str) -> "list[str]":
    """What must be true of the page the public would get."""
    bad = []

    if "noindex" in html:
        bad.append("live: still noindex — the page would never be found")
    # The palette toggle this used to look for no longer exists
    # anywhere, so that assertion could not fail — and a check that
    # cannot fail is worse than none, because it is still counted.
    # What matters now is that the published page ARRIVES IN CREAM:
    # no palette baked into the HTML, nothing read before first paint.
    if "data-palette=" in html:
        bad.append("live: a palette is baked into the published page. Every "
                   "visit begins in cream, and only a press on the page "
                   "changes that")
    # The BADGE, not the words. The demo's placeholder alt text reads
    # "Stand-in photograph…", so matching the phrase anywhere made a
    # check that could never pass — and a check that always fails is
    # read once and ignored afterwards.
    #
    # The badge is the thing that nearly shipped: it was tied to the
    # presence of an image rather than to whether the image was a
    # placeholder, so on launch day it would have been printed across
    # the client's own photographs.
    # The footer's "link to configure" label is the studio's own note to
    # itself. content-check.py already refuses to publish an unset social
    # link, so this is the second lock on the same door — the first one is
    # a rule in a script, and this one is what the browser actually got.
    if "link to configure" in html:
        bad.append(
            "live: a social link still shows the studio's placeholder label"
        )

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
    # The reader, on the exact shape that fooled it: a probe that wrote
    # no verdict, with the sentinel sitting in its own source below.
    assert only_the_verdict(
        '<p id="o">no verdict</p><script>t = "PATCH " + s;</script>'
    ) == "no verdict", "only_the_verdict is reading the dump again"

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
            # Every light on the real page, in all six arrangements —
            # the probe build below has only one reference with
            # projects, so it would exercise one of the six.
            problems += check_unspent(chrome, out, url)
            problems += check_lights(chrome, out, url)

            # Contact in the band ends at the form, and the shape that
            # says so is on both buttons that open it.
            problems += check_menu(chrome, out, url)
            problems += check_reach(chrome, out, url)
            site_css = Path("static/css/site.css").read_text(encoding="utf-8")
            problems += check_shape_css(site_css)
            problems += check_takes_turns(site_css)
            problems += check_marks_declared(site_css)
            problems += check_marks(chrome, out, url, site_css)
            problems += check_arc(chrome, out, url)
            problems += check_document(chrome, out, url)
            problems += check_tint(chrome, out, url)
            problems += check_fixed(chrome, out, url)
            problems += check_patchwork(chrome, out, url)
            problems += check_toolbar(chrome, out, url)
            problems += check_lost(chrome, out, url)
            problems += check_no_pdf_served(out)
            problems += check_crossing(chrome, out, url, False)
            problems += check_crossing(chrome, out, url, True)
            problems += check_cloud_css(site_css)
            problems += check_loops_close(site_css)
            problems += check_cloud(chrome, out, url, False)
            problems += check_cloud(chrome, out, url, True)

            for w, h, name, anchor in SIZES:
                html = dom(chrome, url + anchor, w, h, shots / f"{name}.png")
                if not html.strip():
                    problems.append(f"{name}: the browser returned nothing")
                    continue
                problems += check(html, name)
                problems += check_shape(html, name)
                problems += check_form_words(html, name)

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
            # --- a project added but not yet filled ----------------
            #
            # Between pressing "add a project" in the panel and dropping
            # the first photograph, this is what the content looks like.
            # It stopped the build, and nothing said so.
            waiting_root = build_with_a_waiting_project(out)
            waited = subprocess.run(
                ["zola", "--root", str(waiting_root), "build",
                 "--base-url", url, "-o", str(out), "-f"],
                capture_output=True, text=True,
            )
            if waited.returncode != 0:
                problems.append(
                    "the site does not build when a project is waiting for "
                    "its first photograph — which is every project, between "
                    "the panel making it and anyone filling it:\n"
                    + waited.stderr[-400:])
            else:
                shown = re.findall(r"patch-count[^>]*>([0-9]+) projects",
                                   (out / "index.html").read_text(encoding="utf-8"))
                if shown and shown[0] != "5":
                    problems.append(
                        f"waiting: reference 1 counts {shown[0]} projects with "
                        f"an empty one added; it has five that can be shown")

            # And the configuration that will face the public.
            # --- a reference that has projects ---------------------
            probe_root = build_with_projects(out)
            made = subprocess.run(
                ["zola", "--root", str(probe_root), "build",
                 "--base-url", url, "-o", str(out), "-f"],
                capture_output=True, text=True,
            )
            if made.returncode != 0:
                problems.append("the site does not build with projects in it:\n"
                                + made.stderr[-400:])
            else:
                problems += check_gallery(dom(chrome, url, 500, 1400))
                # And with no script at all: <details> and scroll-snap are
                # the whole mechanism, so the gallery must not need one.
                problems += check_gallery(dom(chrome, url, 500, 1400, None, no_js=True))
                problems += check_reopen(chrome, out, url)
                problems += check_named_spot(chrome, out, url)
                problems += check_escape(chrome, out, url)
                problems += check_edges(chrome, out, url)
                problems += check_cover(chrome, out, url)

            # And with a strip copy smaller than the one that opens,
            # which is what real photography looks like and the
            # stand-ins do not.
            # A headline in two typefaces. Nothing in the real content
            # is marked up — the request was to leave the room, not to
            # fill it — so the check needs a build that uses it.
            faces_root = build_with_two_faces(out)
            made_faces = subprocess.run(
                ["zola", "--root", str(faces_root), "build",
                 "--base-url", url, "-o", str(out), "-f"],
                capture_output=True, text=True)
            if made_faces.returncode != 0:
                problems.append("the site does not build with a headline in "
                                "two faces:\n" + made_faces.stderr[-400:])
            else:
                problems += check_two_faces(chrome, out, url)

            small_root = build_with_a_small_strip(out)
            made_small = subprocess.run(
                ["zola", "--root", str(small_root), "build",
                 "--base-url", url, "-o", str(out), "-f"],
                capture_output=True, text=True)
            if made_small.returncode != 0:
                problems.append("the site does not build with a smaller strip "
                                "copy:\n" + made_small.stderr[-400:])
            else:
                problems += check_horizon_ceiling(chrome, out, url)

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
