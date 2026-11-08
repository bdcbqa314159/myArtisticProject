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


# A reference with a full fridge on it, rendered for real.
#
# The probe REPLACES the page's portfolio rather than adding to it: a
# reference takes five projects and the real page already has five on
# some of them, so appending pushed it over the cap and the extra
# projects were on no page — the check then reported its own
# photographs missing.
WITH_PROJECTS = """
[[extra.project]]
id = "probe-a"
reference = 1
name = "Probe A"

[[extra.project]]
id = "probe-b"
reference = 1
name = "Probe B"

[[extra.project]]
id = "probe-c"
reference = 1
name = "Probe C"

[[extra.project]]
id = "probe-d"
reference = 1
name = "Probe D"

[[extra.project]]
id = "probe-e"
reference = 1
name = "Probe E"

[[extra.photo]]
project = "probe-a"
file = "fragment-01.jpg"
alt = "Probe photograph one"

[[extra.photo]]
project = "probe-a"
file = "fragment-02.jpg"
alt = "Probe photograph two"

[[extra.photo]]
project = "probe-b"
file = "fragment-03.jpg"
alt = "Probe photograph three"

[[extra.photo]]
project = "probe-c"
file = "fragment-02.jpg"
alt = "Probe cover c"

[[extra.photo]]
project = "probe-d"
file = "fragment-03.jpg"
alt = "Probe cover d"

[[extra.photo]]
project = "probe-e"
file = "fragment-04.jpg"
alt = "Probe cover e"
"""


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
MENU_PROBE = """
<meta charset=utf-8><body><p id=o>?</p><script>
const f = document.createElement("iframe");
f.width = 390; f.height = 700; f.style.border = 0; f.src = "/";
document.body.appendChild(f);
const say = (s) => { document.getElementById("o").textContent = "MENU " + s; };
f.addEventListener("load", () => setTimeout(() => {
  const d = f.contentDocument;
  const box = d.querySelector("dialog.talk");
  if (!box) return say("no-form");
  if (box.open) return say("form-already-open");

  // Any link into Contact. There is exactly one, and it is the band's.
  const link = d.querySelector('.links a[href="#contact"], .links a[href$="#contact"]');
  if (!link) return say("no-contact-link");

  // A control: something else in the band must NOT open it.
  const other = [...d.querySelectorAll(".links a")]
    .find((a) => !a.getAttribute("href").endsWith("#contact"));
  if (!other) return say("no-control-link");
  other.click();

  /* Read AFTER a turn, not before one. The page defers the whole chain
   * through a `setTimeout`, so reading `open` on the same tick as the
   * click says "closed" no matter what the code does — which is how
   * this control first passed against a page that opened the form for
   * every link in the band. */
  setTimeout(() => {
    const afterOther = box.open;
    link.click();
    setTimeout(() => {
      /* Read the band's result into its own variable HERE, before
       * anything else is clicked. It was reported from `box.open` at the
       * very end, after the probe had opened the form itself to look at
       * the focus — so it said "the band works" no matter what the band
       * did, and a mutation that opened the form only when the scroll
       * landed passed cleanly. */
      const fromTheBand = box.open;
      /* And the two openers are still BUTTONS.
       *
       * The shape class was first called `.talk`, which is the dialog's
       * class — it carries `border: 0; padding: 0; width: 100%`, so both
       * buttons went full-width with no outline, and every check passed.
       * A border and a padding of zero cannot be right for a button on
       * this page whatever its label says, so those are what is read. */
      const flat = [...d.querySelectorAll("[data-talk]")].filter((b) => {
        const cs = f.contentWindow.getComputedStyle(b);
        return parseFloat(cs.borderTopWidth) < 0.5
            || parseFloat(cs.paddingLeft) < 1;
      }).length;

      /* Where the cursor lands, and whether the browser drew its own
       * ring. Both have been wrong: the ring appeared around the whole
       * window because the page focused the dialog as if it were a
       * section, and the cursor landed in the honeypot because
       * `showModal` takes the first focusable element and `tabindex=-1`
       * still qualifies. */
      box.close();
      d.querySelector("[data-talk]").click();
      setTimeout(() => {
        const a = d.activeElement;
        const cs = f.contentWindow.getComputedStyle(a);
        say("contact=" + fromTheBand + " control=" + afterOther
          + " flat=" + flat
          + " lands=" + (a.getAttribute("name") || a.tagName.toLowerCase())
          + " ring=" + (cs.outlineStyle === "none" ? "no" : cs.outlineStyle));
      }, 150);
    }, 120);
  }, 120);
}, 400));
</script>"""


def check_menu(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_menu.html").write_text(MENU_PROBE, encoding="utf-8")
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
MARKS_PROBE = """
<meta charset=utf-8><body style=margin:0><p id=o>?</p><script>
const f = document.createElement("iframe");
f.width = 390; f.height = 700; f.style.border = 0; f.src = "/";
document.body.appendChild(f);
const luma = (s) => {
  const m = (s.match(/[\\d.]+/g) || [0, 0, 0]).map(Number);
  return 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2];
};
f.addEventListener("load", () => setTimeout(() => {
  const d = f.contentDocument, w = f.contentWindow;
  const links = d.querySelectorAll(".dock a").length;
  const out = [];
  for (const p of __PALETTES__) {
    if (p === "") delete d.documentElement.dataset.palette;
    else d.documentElement.dataset.palette = p;
    const pale = luma(w.getComputedStyle(d.body).backgroundColor) > 128;
    const shown = [...d.querySelectorAll(".dock .mark")]
      .filter((i) => w.getComputedStyle(i).display !== "none")
      .map((i) => i.currentSrc);
    // One mark per link, and its tone is the one the ground can show.
    const wrong = shown.filter((u) => u.includes(pale ? "white" : "black")).length;
    out.push((p || "default") + ":" + (shown.length === links ? "n" : "COUNT")
      + (wrong === 0 ? "ok" : "WRONG"));
  }
  document.getElementById("o").textContent = "MARKS links=" + links
    + " " + out.join(" ");
}, 700));
</script>"""


def check_marks(chrome: str, out: Path, url: str, css: str) -> "list[str]":
    """Measured: what shows, against the ground it shows on."""
    names = sorted(set(re.findall(r'\[data-palette="([a-z]+)"\]', css)))
    (out / "_marks.html").write_text(
        MARKS_PROBE.replace("__PALETTES__", json.dumps([""] + names)),
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
ARC_PROBE = """
<meta charset=utf-8><body style=margin:0><p id=o>no verdict</p><script>
const out = []; let done = 0;
const SIZES = [[390, 700], [900, 800]];
SIZES.forEach(([w, h]) => {
  const f = document.createElement("iframe");
  f.width = w; f.height = h; f.style.border = 0; f.src = "/";
  document.body.appendChild(f);
  f.addEventListener("load", () => setTimeout(() => {
    try {
      const d = f.contentDocument;
      const sw = d.querySelector(".swap");
      const ph = [...d.querySelectorAll(".swap .phrase")];
      if (!sw || ph.length !== 2) { out.push(w + ":no-heading"); }
      else {
        sw.classList.add("swapping");
        const a = ph.map((p) => p.getAnimations()[0]);
        if (a.some((x) => !x)) { out.push(w + ":no-animation"); }
        else {
          a.forEach((x) => x.pause());
          /* The INK, not the block. The heading is centred, so the
           * block reaches the gutter with empty margin on both sides
           * and its own left edge may cross the viewport without a
           * single letter doing so. Measuring the block failed a sweep
           * that was comfortably inside the page. */
          const inkOf = (p) => {
            const r = d.createRange();
            r.selectNodeContents(p);
            const box = r.getBoundingClientRect();
            return box.width > 0 ? box : p.getBoundingClientRect();
          };
          const at = (t) => { a.forEach((x) => { x.currentTime = t; });
                              return ph.map(inkOf); };

          /* Home is where the phrases rest with NO animation and no
           * waiting offset — read before any of this starts. Taking it
           * from the animation's own last frame instead made "did they
           * land home" compare the end against itself, so a version
           * that finished six pixels off passed. */
          sw.classList.remove("swapping");
          ph.forEach((p) => { p.style.transform = ""; });
          const home = ph.map(inkOf);
          sw.classList.add("swapping");
          a.length = 0;
          ph.forEach((p) => a.push(p.getAnimations()[0]));
          a.forEach((x) => x.pause());
          let bow = 0, edge = 1e9, travel = 0, cross = 1e9, crossGap = 0, rightward = 0;
          for (let i = 0; i <= 24; i++) {
            const r = at(480 + 820 * i / 24);
            for (let k = 0; k < 2; k++) {
              const dx = r[k].left - home[k].left;
              if (dx > 0.5) rightward++;            // a C never goes right
              bow = Math.max(bow, -dx);
              travel = Math.max(travel, Math.abs(r[k].top - home[k].top));
            }
            edge = Math.min(edge, r[0].left, r[1].left);
            const dy = Math.abs(r[0].top - r[1].top);
            if (dy < cross) { cross = dy; crossGap = Math.abs(r[0].left - r[1].left); }
          }
          const end = at(1300);
          const landed = ph.every((p, k) =>
            Math.abs(end[k].left - home[k].left) < 0.5
            && Math.abs(end[k].top - home[k].top) < 0.5);
          out.push(w + ":bow=" + Math.round(bow) + ":travel=" + Math.round(travel)
            + ":edge=" + Math.round(edge) + ":gap=" + Math.round(crossGap)
            + ":right=" + rightward + ":home=" + landed);
        }
      }
    } catch (err) { out.push(w + ":threw-" + err.message); }
    if (++done === SIZES.length) {
      document.getElementById("o").textContent = "ARC " + out.join(" ");
    }
  }, 900));
});
</script>"""


def check_arc(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_arc.html").write_text(ARC_PROBE, encoding="utf-8")
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
CLOUD_PROBE = """
<meta charset=utf-8><body style=margin:0><p id=o>no verdict</p><script>
const out = []; let done = 0;
const SIZES = [[390, 700], [900, 800]];
SIZES.forEach(([w, h]) => {
  const f = document.createElement("iframe");
  f.width = w; f.height = h; f.style.border = 0; f.src = "/";
  document.body.appendChild(f);
  f.addEventListener("load", () => setTimeout(() => {
    try {
      const d = f.contentDocument, win = f.contentWindow;
      const drops = [...d.querySelectorAll(".cloud .drop")];
      if (!drops.length) { out.push(w + ":none"); }
      else {
        const anims = drops.flatMap((p) => p.getAnimations());

        /* Scroll-driven animation has a ScrollTimeline instead of the
         * document's. This is the assertion for "they do not move when
         * the page moves". */
        const scrolly = anims.filter(
          (a) => a.timeline && a.timeline !== d.timeline).length;

        // Six words swinging on the same clock is a metronome.
        const periods = new Set(anims.map(
          (a) => String(a.effect.getTiming().duration)));

        /* Held while the page moves, moving again once it settles.
         * A real `scroll` event is dispatched; what is read back is the
         * computed `animation-play-state`, which is the browser's own
         * answer rather than the class the page sets. */
        win.dispatchEvent(new Event("scroll"));
        const whileScrolling = win.getComputedStyle(drops[0]).animationPlayState;

        // Button-ness, which is what was wrong with them before.
        const boxed = drops.filter((p) => {
          const cs = win.getComputedStyle(p);
          return parseFloat(cs.borderTopWidth) > 0.5
              || (cs.backgroundColor !== "rgba(0, 0, 0, 0)"
                  && cs.backgroundColor !== "transparent");
        }).length;

        const fonts = new Set(drops.map(
          (p) => win.getComputedStyle(p).fontSize));

        /* Every drift driven to both of its ends at once — the widest
         * the field can ever be. A page that only fits while the words
         * happen to be centred is a page that overflows later. */
        /* Where the words can get to, sampled.
         *
         * Driving every drift to the SAME end is not the worst case —
         * the three clocks on each word are independent, so over a few
         * minutes every combination of phases happens. A deterministic
         * pseudo-random walk over 64 of them is a fair picture of what
         * the field actually does; driving them all to one end only
         * tests the one arrangement that never occurs.
         *
         * `scrollWidth` is no witness here either: the page sets
         * `overflow-x: clip`, so a word pushed past the edge is
         * silently cut rather than scrolled to. The words' own rectangles
         * are what gets measured. */
        let over = 0, collide = 0;
        if (scrolly === 0) {
          anims.forEach((a) => a.pause());
          let seed = 20261108;
          const next = () => (seed = (seed * 1103515245 + 12345) % 2147483648)
                             / 2147483648;
          for (let sample = 0; sample < 200; sample++) {
            anims.forEach((a) => {
              a.currentTime = next() * a.effect.getTiming().duration;
            });
            const r = drops.map((p) => p.getBoundingClientRect());
            for (let i = 0; i < r.length; i++) {
              if (r[i].left < 0 || r[i].right > d.documentElement.clientWidth) over++;
              for (let j = i + 1; j < r.length; j++) {
                if (!(r[i].right <= r[j].left || r[j].right <= r[i].left
                   || r[i].bottom <= r[j].top || r[j].bottom <= r[i].top)) collide++;
              }
            }
          }
        }
        out.push(w + ":held=" + whileScrolling
          + ":n=" + drops.length + ":anims=" + anims.length
          + ":scrolly=" + scrolly + ":periods=" + periods.size
          + ":boxed=" + boxed + ":fonts=" + fonts.size + ":over=" + over
          + ":collide=" + collide + ":layer=" + (win.getComputedStyle(drops[0])
              .willChange.includes("transform") ? "yes" : "no"));
      }
    } catch (err) {
      out.push(w + ":threw-" + String(err.message).replace(/[^A-Za-z0-9]+/g, "-"));
    }
    if (++done === SIZES.length) {
      document.getElementById("o").textContent = "CLOUD " + out.join(" ");
    }
  }, 900));
});
</script>"""


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
    (out / "_cloud.html").write_text(CLOUD_PROBE, encoding="utf-8")
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
CROSS_PROBE = """
<meta charset=utf-8><body style=margin:0><p id=o>no verdict</p><script>
const f = document.createElement("iframe");
f.width = 390; f.height = 700; f.style.border = 0; f.src = "/";
document.body.appendChild(f);
f.addEventListener("load", () => setTimeout(() => {
  try {
    const d = f.contentDocument, w = f.contentWindow;
    const root = d.documentElement;
    const bar = d.querySelector("header");
    const veil = d.querySelector(".veil");
    const link = d.querySelector('.links a[href$="#about"]');
    const btn = d.querySelector(".hero .btn.primary");
    if (!veil || !link || !btn) { say("missing"); return; }

    const inert = w.getComputedStyle(veil).pointerEvents === "none" ? "y" : "n";
    const about = d.getElementById("about");
    const want = Math.round(w.scrollY + about.getBoundingClientRect().top
                            - bar.getBoundingClientRect().height);
    link.click();
    setTimeout(() => {
      const during = root.classList.contains("crossing") ? "y" : "n";
      const landed = Math.abs(w.scrollY - want) <= 2 ? "y" : "n";
      setTimeout(() => {
        const after = root.classList.contains("crossing") ? "y" : "n";
        const held = Math.abs(w.scrollY - want) <= 2 ? "y" : "n";
        w.scrollTo({ top: 0, behavior: "instant" });
        setTimeout(() => {
          btn.click();
          setTimeout(() => {
            // A travelling link cannot arrive here. A crossing one would.
            const btnCrossed = root.classList.contains("crossing")
                               || w.scrollY > 2 ? "y" : "n";
            say("inert=" + inert + " during=" + during + " landed=" + landed
              + " after=" + after + " held=" + held + " btn=" + btnCrossed
              + " want=" + want);
          }, 500);
        }, 100);
      }, 640);
    }, 330);
  } catch (err) { say("threw-" + String(err.message).replace(/[^A-Za-z0-9]+/g, "-")); }
}, 900));
function say(s) { document.getElementById("o").textContent = "CROSS " + s; }
</script>"""


def check_crossing(chrome: str, out: Path, url: str, still: bool) -> "list[str]":
    (out / "_cross.html").write_text(CROSS_PROBE, encoding="utf-8")
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
DOC_PROBE = """
<meta charset=utf-8><body style=margin:0><p id=o>no verdict</p><script>
const f = document.createElement("iframe");
f.width = 390; f.height = 720; f.style.border = 0; f.src = "/";
document.body.appendChild(f);
/* WAIT FOR THE COVER TO GO.
 * Acting on a fixed delay made this measurement flap: sometimes the
 * page was still behind its loader, the click on the summary landed on
 * the cover instead of the page, and the document never opened — which
 * showed up as `pos=static covers=n` on one run and a clean pass on the
 * next. A reader waits for the page; so does this. */
function whenReady(d, go, waited) {
  // `booting` is the class the page itself takes off when the cover has
  // done its work. Not the element: in a frame that one can outlive the
  // class, and waiting on it waits for ever.
  const covered = d.documentElement.classList.contains("booting");
  if (!covered || (waited || 0) > 6000) { go(); return; }
  setTimeout(() => whenReady(d, go, (waited || 0) + 100), 100);
}

f.addEventListener("load", () => setTimeout(() => {
  try {
    const d = f.contentDocument, w = f.contentWindow;
    const box = d.querySelector("details.dossier");
    if (!box) { say("none"); return; }
    whenReady(d, () => measure(d, w, box));
  } catch (err) { say("threw-" + String(err.message).replace(/[^A-Za-z0-9]+/g, "-")); }
}, 300));

function measure(d, w, box) {
  try {

    /* Everything in the reveal released, as it is for anyone who has
     * scrolled to the card. The reveal puts a `transform` on the <ol>,
     * and a transformed ancestor is the containing block for anything
     * `position: fixed` inside it — which would make the reading
     * surface a box inside the card instead of the page. Measured: 343
     * x 757 at 23,-136 before the reveal; the viewport after it. */
    d.querySelectorAll(".reveal").forEach((e) => {
      /* The transition taken off FIRST. `.in` only sets the end state,
       * and the 650ms journey to it keeps a `transform` on the element
       * the whole way — so measuring half a second after adding the
       * class caught it mid-flight, and `covers` came out true on one
       * run and false on the next. Setting it through the element's own
       * style is CSSOM, which `style-src 'self'` allows; an injected
       * <style> element would be blocked. */
      e.style.transition = "none";
      e.classList.add("in");
    });

    const leaves = box.querySelector(".leaves");
    const pages = leaves.querySelectorAll(".leaf").length;
    // Anything at all that could hand the reader a file.
    const links = box.querySelectorAll("a[href], [download]").length;

    box.querySelector("summary").click();
    setTimeout(() => {
      /* READ IT NOW, not in `say()`. `getComputedStyle` returns a LIVE
       * object: holding on to it and reading `.position` three timeouts
       * later reported `static` every time, because by then the ground
       * click had closed the document. The booleans beside it were
       * computed eagerly and said the opposite, which is what gave a
       * verdict of `pos=static covers=y` — two measurements of the same
       * element at different moments, dressed as one. */
      const pos = w.getComputedStyle(leaves).position;
      const r = leaves.getBoundingClientRect();
      /* Against the DOCUMENT's client box, not `innerWidth`.
       * `innerWidth` includes the scrollbar; a fixed element does not.
       * On a Mac, where scrollbars are overlays, the two agree and this
       * passed. On the Linux runner, where a scrollbar takes 15 real
       * pixels, it failed — a platform difference reported as a page
       * fault. The check was wrong, not the page. */
      const vw = d.documentElement.clientWidth;
      const vh = d.documentElement.clientHeight;
      const covers = Math.abs(r.width - vw) < 2 && Math.abs(r.height - vh) < 2
                  && Math.abs(r.left) < 2 && Math.abs(r.top) < 2;
      /* Scrollable, not merely overflowing. A box with `overflow:
       * visible` still reports a scrollHeight past its clientHeight —
       * the content spills instead of scrolling — so taking the
       * stylesheet's `overflow-y` away left this test green while the
       * pages ran off the bottom of the screen with no way to reach
       * them. Both halves are needed: room to scroll, and permission. */
      const oy = w.getComputedStyle(leaves).overflowY;
      const scrolls = leaves.scrollHeight > leaves.clientHeight + 10
                   && (oy === "auto" || oy === "scroll");
      const leaf = leaves.querySelector(".leaf");
      const sharp = leaf.naturalWidth / Math.max(1, leaf.getBoundingClientRect().width);

      leaf.click();                       // reading, not leaving
      setTimeout(() => {
        const stillOpen = box.open;
        leaves.click();                   // the margin, which is leaving
        setTimeout(() => {
          say("pages=" + pages + " links=" + links
            + " pos=" + pos
            + " covers=" + (covers ? "y" : "n")
            + " scrolls=" + (scrolls ? "y" : "n")
            + " sharp=" + sharp.toFixed(1)
            + " onpage=" + (stillOpen ? "stays" : "CLOSED")
            + " onground=" + (box.open ? "STAYS" : "closes"));
        }, 150);
      }, 150);
    }, 500);
  } catch (err) { say("threw-" + String(err.message).replace(/[^A-Za-z0-9]+/g, "-")); }
}
function say(s) { document.getElementById("o").textContent = "DOC " + s; }
</script>"""


def check_document(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_doc.html").write_text(DOC_PROBE, encoding="utf-8")
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


def strip_portfolio(page: str) -> str:
    out, skip = [], False
    for line in page.splitlines(keepends=True):
        if line.startswith("[[extra.project]]") or line.startswith("[[extra.photo]]"):
            skip = True
            continue
        if skip and (line.startswith("[[") or line.startswith("# ----")):
            skip = False
        if not skip:
            out.append(line)
    return "".join(out)


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
REOPEN_PROBE = """
<script>
addEventListener("load", () => setTimeout(() => {
  const out = document.getElementById("verdict");
  const group = document.querySelector(".group");
  const shots = group && group.querySelector(".shots");
  if (!group || !shots) { out.textContent = "RESULT no-gallery"; return; }
  group.open = true;
  shots.open = true;
  const both = group.open && shots.open;
  group.open = false;
  setTimeout(() => {
    const left = shots.open;
    group.open = true;
    setTimeout(() => {
      // THE GROUND IS THE WAY OUT, one level at a time.
      // A carousel closes back to the group it came from, not out of
      // both — so the reader lands where they were, not at the start.
      const front = group.querySelector(".group-front");
      const reel = shots.querySelector(".reel");
      shots.open = true;
      reel.dispatchEvent(new MouseEvent("click", {bubbles: true}));
      setTimeout(() => {
        const afterReel = "carousel=" + shots.open + " group=" + group.open;
        front.dispatchEvent(new MouseEvent("click", {bubbles: true}));
        setTimeout(() => {
          out.textContent = "RESULT both=" + both + " left=" + left
            + " reopened=" + shots.open + " " + afterReel
            + " afterFront=" + group.open;
        }, 20);
      }, 20);
    }, 20);
  }, 20);
}, 0));
</script>"""


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
        + sec.group(0) + '</main>' + js.group(0) + REOPEN_PROBE + '</html>',
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
COVER_PROBE = """
<meta charset=utf-8><body><p id=o>?</p><script>
const f = document.createElement("iframe");
f.width = 390; f.height = 700; f.style.border = 0; f.src = "/";
document.body.appendChild(f);
let seen = null, gone = null;
const t0 = performance.now();
const tick = () => {
  let d = null;
  try { d = f.contentDocument; } catch (e) {}
  const booting = d && d.documentElement
    && d.documentElement.classList.contains("booting");
  if (booting && seen === null) seen = performance.now();
  if (seen !== null && !booting && gone === null) gone = performance.now();
  if (gone !== null || performance.now() - t0 > 8000) {
    document.getElementById("o").textContent = "COVERED-FOR "
      + (seen === null ? "never-covered" : gone === null ? "never-uncovered"
         : Math.round(gone - seen));
    return;
  }
  setTimeout(tick, 5);
};
tick();
</script>"""


def check_cover(chrome: str, out: Path, url: str) -> "list[str]":
    (out / "_cover.html").write_text(COVER_PROBE, encoding="utf-8")
    said = dom(chrome, url + "/_cover.html", 500, 900)
    found = re.search(r"COVERED-FOR ([a-z0-9-]+)", said)
    if not found:
        return ["cover: the probe returned no verdict"]
    verdict = found.group(1)
    if not verdict.isdigit():
        return [f"cover: {verdict}"]
    held = int(verdict)
    if held < 380:
        return [f"cover: on screen for {held}ms — short enough to read as a "
                "flicker rather than as a page arriving"]
    if held > 2000:
        return [f"cover: on screen for {held}ms with nothing to wait for, "
                "which is a page being held back for no reason"]
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
LIGHT_PROBE = """
<script>
const slotOf = (el) => {
  const s = el && el.closest(".shots");
  if (!s) return 0;
  const m = s.className.match(/slot-(\\d)/);
  return m ? Number(m[1]) : 0;
};
addEventListener("load", () => setTimeout(() => {
  const hidden = [];
  let seen = 0;
  document.querySelectorAll(".group").forEach((g, gi) => {
    g.open = true;
    g.querySelectorAll(".look").forEach((look) => {
      seen++;
      const mine = slotOf(look);
      const r = look.getBoundingClientRect();
      const pts = [[r.left + r.width/2, r.top + r.height/2],
                   [r.left + 3, r.top + 3], [r.right - 3, r.top + 3],
                   [r.left + 3, r.bottom - 3], [r.right - 3, r.bottom - 3]];
      const over = pts.filter(([x, y]) =>
        slotOf(document.elementFromPoint(x, y)) > mine).length;
      if (over > 1) hidden.push("set" + (gi+1) + " slot" + mine + " (" + over + "/5)");
    });
    g.open = false;
  });
  document.getElementById("out").textContent =
    "LIGHTS seen=" + seen + " hidden=" + (hidden.join(", ") || "none");
}, 60));
</script>"""


def check_lights(chrome: str, out: Path, url: str) -> "list[str]":
    page = (out / "index.html").read_text(encoding="utf-8")
    css = re.search(r'<link[^>]*site\.css[^>]*>', page)
    sec = re.search(r'<section id="?work"?.*?</section>', page, re.S)
    if not (css and sec):
        return ["lights: could not assemble the probe page"]
    (out / "_lights.html").write_text(
        '<!doctype html><html lang=en class=js><meta charset=utf-8>'
        + css.group(0) + '<body><p id=out>?</p><main>' + sec.group(0)
        + '</main>' + LIGHT_PROBE + '</html>', encoding="utf-8")
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


def build_with_projects(out: Path) -> Path:
    """A whole site, copied, with one reference's fridge filled in.

    A COPY, not the real content file. Zola's content directory is
    fixed, so rendering a different page means either editing the
    tracked one and hoping to put it back, or building somewhere else.

    BESIDE the output, never inside it: `zola build -o <out> -f` wipes
    the output directory first, so a source root nested in it deletes
    itself on the way to being built.
    """
    root = out.with_name(out.name + "-with-projects")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name in ("content", "templates", "static"):
        shutil.copytree(ROOT / name, root / name,
                        ignore=shutil.ignore_patterns("processed_images"))
    shutil.copy2(ROOT / "config.toml", root / "config.toml")

    page = root / "content" / "_index.md"
    text = strip_portfolio(page.read_text(encoding="utf-8"))
    mark = "# ---- 04 original concepts"
    text = (text.replace(mark, WITH_PROJECTS + "\n" + mark, 1)
            if mark in text else text.replace("+++", WITH_PROJECTS + "\n+++", 1))
    page.write_text(text, encoding="utf-8")
    return root


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
            site_css = Path("static/css/site.css").read_text(encoding="utf-8")
            problems += check_shape_css(site_css)
            problems += check_marks_declared(site_css)
            problems += check_marks(chrome, out, url, site_css)
            problems += check_arc(chrome, out, url)
            problems += check_document(chrome, out, url)
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
