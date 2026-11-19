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
from variants import (build_live_config, build_with_a_waiting_project,  # noqa: E402
                      build_with_projects)
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
    said = dom(chrome, url + "/_cross.html", 500, 900, reduced=still)
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
    if f["btn"] != "n":
        bad.append("cross: the hero button crosses too. It is meant to keep "
                   "its long scroll — that journey is the point there, and "
                   "it is the one the client asked to keep")
    return bad


# A document is shown and not served.


def check_document(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_doc.html").write_text(probe("doc"), encoding="utf-8")
    said = dom(chrome, url + "/_doc.html", 500, 900, budget=20000)
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
        bad.append(f"tint: scrolling changed the light ({verdict}). Only going "
                   f"into the work does that")
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
    if f["elsewhere"] != f["returned"]:
        bad.append(f"tint: a menu entry that is not Selected Work changed the "
                   f"light ({verdict}). Going into the WORK is what changes "
                   f"it, not navigating")
    if f["viamenu"] != f["clicked"]:
        bad.append(f"tint: Selected Work in the menu does not do what the hero "
                   f"button does ({verdict}). It should not matter which door "
                   f"was used — and this is also the second visit, so it "
                   f"proves the trigger works again after coming back")
    return bad


# The open patchwork takes the screen, and its photograph fills it.


def check_patchwork(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_patch.html").write_text(probe("patch"), encoding="utf-8")
    said = dom(chrome, url + "/_patch.html", 1450, 950, budget=25000)
    found = re.search(r"PATCH ([^<]*)", said)
    if not found:
        return ["patch: the probe returned no verdict"]
    bad = []
    for word in found.group(1).split():
        width, _, rest = word.partition(":")
        if "=" not in rest:
            bad.append(f"patch: at {width}px the probe could not run — {rest}")
            continue
        f = dict(kv.split("=") for kv in rest.split(":"))

        # 80% of each side. A 3:2 box in a 390x720 screen manages 32% of
        # the height — measured, before it was told to take the screen's
        # own shape — so this is the assertion that tells the two apart.
        if int(f["wide"]) < 80 or int(f["tall"]) < 80:
            bad.append(f"patch: at {width}px the open patchwork is "
                       f"{f['wide']}% wide and {f['tall']}% tall. It is meant "
                       f"to take the screen, at the screen's own shape")
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
    said = dom(chrome, url + "/_cover.html", 500, 900)
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
                   "visit begins in cream, and only going into the work "
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
                problems += check_cover(chrome, out, url)

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
