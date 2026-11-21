#!/usr/bin/env python3
"""Structural invariants: the things that must be true once, and only once.

    python3 tools/invariants.py

Every defect that reached the client this week was a SEQUENCING or
DUPLICATION defect, not a logic one — motion prepared after the cover
lifted, a blend mode isolated by an opacity threshold, scroll restored
under a cover, and two separate mechanisms both revealing the page.

None of them is visible to a type checker, and none is visible in a
diff: each piece was correct on its own. But duplication is greppable,
and the worst of them — two reveals running in sequence, so the cover
vanished and then came back — would have been caught here the moment it
landed.

This is a cheap instrument, not a substitute for looking at the page.
It catches a specific and recurring class of mistake, which is worth
more than it costs.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# (what it is, file, pattern, how many there must be, why)
INVARIANTS = [
    (
        "nothing starts the page without a net",
        "src/landing.ts",
        r"(?m)^[a-z][A-Za-z0-9_]*\(\);$",
        0,
        "A module is one statement after another: the first that throws "
        "ends the whole of it. These were thirteen bare calls in a row, "
        "and a fault injected at the third left the page behind its "
        "cover for the full six seconds of the head's failsafe and then "
        "arrived with no navigation at all — no menu, no palette, no "
        "gallery. Every startup step goes through `start()` now, which "
        "catches, names the step in the console, and lets the rest run.",
    ),
    (
        "the cover's floor is actually applied before the page is shown",
        "src/landing.ts",
        r"owedBeforeShowing\(performance\.now\(\), COVER_FLOOR_MS\)",
        1,
        "The arithmetic is checked exactly in tools/cover-check.mjs, and "
        "the browser is only asked whether the cover appeared and left — "
        "timing it was flaky and has been taken out. This is what ties "
        "the two together: without it the floor could be computed "
        "perfectly and never used, and nothing would say so.",
    ),
    (
        "no scroll is left to the stylesheet to interpret",
        "src/landing.ts",
        r"window\.scrollTo\(0,",
        0,
        "The two-argument form obeys `scroll-behavior`, and this page's "
        "stylesheet says `smooth`. Every frame of our own easing then "
        "asked the browser to smoothly scroll somewhere new, and the "
        "journey reported itself finished while the page was still "
        "moving — so the navigation band released its marker early. "
        "Measured: `scrollTo(0, 500)` under smooth leaves scrollY at 0 "
        "after 630ms. Say `behavior: \"instant\"` and mean it.",
    ),
    (
        "one place decides the page is ready",
        "src/landing.ts",
        r'readyState === "complete"',
        1,
        "Two of these ran in sequence once: the first removed `booting`, "
        "which takes the cover away instantly, and the second added "
        "`.is-leaving`, which put it back. Page, loader, page — on every "
        "load, for hours, invisible to every other check here.",
    ),
    (
        "one place shows the loader's leaving state",
        "src/landing.ts",
        r'classList\.add\("is-leaving"\)',
        1,
        "The cover is displayed by `.booting` or by `.is-leaving`. A "
        "second place adding the latter can re-show a cover that has "
        "already gone.",
    ),
    (
        "the exchange is taken back after it happens",
        "src/motion.ts",
        r'classList\.remove\("swapping"\)',
        1,
        "The brief asks for the two phrases to exchange places ONCE, "
        "sans boucle. `.swapping` is what carries the transition, so "
        "leaving it on means anything that moves those phrases later — "
        "a resize, a late font — animates them again.",
    ),
    (
        "nothing animates the phrases unconditionally",
        "static/css/site.css",
        r'\.swap \.phrase\s*\{[^}]*transition',
        0,
        "The transition belongs to `.swap.swapping .phrase` and to "
        "nothing wider. Written against `.swap .phrase` it is permanent, "
        "and the single exchange becomes a thing that replays whenever "
        "the layout shifts — which is the loop the brief rules out.",
    ),
    (
        "the miniatures blur with everything else",
        "static/css/site.css",
        r"html\.scrolling \.fridge img",
        2,
        "A reference shows a fridge of prints instead of its one "
        "photograph, and the softening was written against the "
        "photograph — so the day the gallery arrived, the effect the "
        "client had approved stopped happening on most of the page and "
        "no check noticed. Twice: the rule, and the reduced-motion reset.",
    ),
    (
        "an open level does not paint over itself",
        "static/css/site.css",
        r"\.group\[open\] > summary,\s*html\.js \.shots\[open\] > summary"
        r" \{ display: none; \}",
        1,
        "Each level hides what opened it — the card's fridge once the "
        "group is at the front, a project's cover once its carousel is. "
        "Scoped to the no-script case by mistake once already, and the "
        "same photograph appeared twice: one full screen, one floating "
        "in a corner.",
    ),
    (
        "an open print stops being transformed",
        "static/css/site.css",
        r"\.shots\[open\] \{\s*position: static;\s*transform: none;",
        1,
        "`transform` makes an element the containing block for every "
        "`position: fixed` descendant, so a carousel inside a rotated "
        "print resolves `inset: 0` against the print instead of the "
        "screen. This page has met that rule twice: once with "
        "`backdrop-filter` on the header, once here.",
    ),
    (
        "the carousel opens on the photograph that was tapped",
        "static/css/site.css",
        r"scroll-snap-align: start;",
        1,
        "Centred, the first photograph sat in the middle with empty "
        "ground to its left, so the reader scrolled backwards to find "
        "out there was nothing there. It opens flush left on the one "
        "that was tapped.",
    ),
    (
        "the group's blur is on a pseudo-element, not on the group",
        "static/css/site.css",
        r"\.group-front \{(?:[^}]*)backdrop-filter",
        0,
        "`backdrop-filter` makes an element the containing block for "
        "every `position: fixed` descendant, and a project's carousel "
        "is one — put the blur on this box and level three anchors to "
        "it instead of the screen. The same rule has caught this page "
        "twice already, with `backdrop-filter` on the header and with "
        "`transform` on a print. The blur belongs on ::before.",
    ),
    (
        "every light has somewhere it can be seen",
        "static/css/site.css",
        r"\.look \{ --look-",
        4,
        "The prints overlap and a later one paints over an earlier one, "
        "so the foot of a print is under its neighbour in three of the "
        "thirty places. Those three, and the background's own, are "
        "named — computed by testing each candidate point against the "
        "rectangles of the prints that paint after it. Lose them and a "
        "light goes missing in a way nobody notices until they look for "
        "it and cannot find it.",
    ),
    (
        "one cover in the markup",
        "templates/index.html",
        r'class="loader"',
        1,
        "Two overlays cannot be reasoned about, and only one of them "
        "would ever be removed.",
    ),
    (
        "every action is pinned to a commit",
        ".github/workflows/deploy.yml",
        r"uses: [^@\n]+@[0-9a-f]{40}",
        6,
        "A tag is a label someone can move, and these jobs hold "
        "`pages: write` and `id-token: write` — an action that changed "
        "under its tag would run with permission to publish this site. "
        "If this count changes, a step was added or removed; pin the new "
        "one by resolving its tag to a commit.",
    ),
    (
        "the landing page has a main landmark",
        "templates/index.html",
        r"<main>",
        1,
        "It was dropped when the template was rebuilt for the maquette's "
        "architecture, and nothing noticed for eleven PRs: no skip-to-content "
        "landmark, and §5 asks for semantic HTML. The accessibility checks "
        "looked at alt text, headings and lang, and never at landmarks.",
    ),
    (
        "one Content-Security-Policy, in the shared head",
        "templates/_head.html",
        r'http-equiv="Content-Security-Policy"',
        1,
        "It used to be copied into each template. A policy tightened in "
        "one place and not the other is the kind of difference nobody "
        "notices until it matters.",
    ),
    (
        "the big copies never invent a pixel",
        "templates/index.html",
        r'op="fit_width", format="webp", quality=76',
        0,
        "The copies swapped in when something opens are the quality-76 "
        "ones. `fit_width` ENLARGES a photograph smaller than the width "
        "asked for: the stand-ins are 1000px and came out as 2000px "
        "files, 16.4MB of invented detail that looked like quality in "
        "every measurement. `op=\"fit\"` inside a 2000px box leaves a "
        "smaller photograph alone — same files, 8.1MB, none of it made "
        "up.",
    ),
    (
        "no style attribute anywhere in the page",
        "templates/index.html",
        r'style="',
        0,
        "The policy is style-src 'self' with no 'unsafe-hashes', so a "
        "style ATTRIBUTE is inline style and the browser drops it. Five "
        "of them sat on the lights for weeks, carrying the only escape "
        "hatch for the arrangements where a light hides under its "
        "neighbour, and it had never once applied. Write it from script "
        "with setProperty, which the policy allows.",
    ),
    (
        "the templates do not carry their own policy",
        "templates/index.html",
        r'http-equiv="Content-Security-Policy"',
        0,
        "It belongs in _head.html, included by both.",
    ),
]


def print_rules_come_last() -> "list[str]":
    """Is `@media print` the last thing in the stylesheet?

    It sat in the middle with 747 lines of screen CSS after it. Nothing
    was broken — none of those rules restated a property the print
    block sets, measured — but a print override that something later
    can beat is a trap for whoever adds the rule that finally does,
    and the only visible symptom would be a printed page.

    Last is also where a reader expects it, which is the other half of
    why the contents block now exists.
    """
    css = read("static/css/site.css")
    at = css.find("@media print")
    if at == -1:
        return ["static/css/site.css has no @media print block at all"]
    after = css[css.index("}", css.rindex("{")) + 1:]
    rules = len(re.findall(r"(?m)^[.#a-zA-Z@:\[][^{}]*\{", css[at:]))
    if rules > 1:
        return [f"@media print is followed by {rules - 1} more rule(s) in "
                f"static/css/site.css. Print comes last: a print override "
                f"that a later rule can beat is a trap, and the only symptom "
                f"is a printed page nobody looks at"]
    return []


def unrun_checks() -> "list[str]":
    """Checks the workflow runs that `npm test` does not.

    The two lists were written separately and drifted: CI grew to
    twenty-two steps while `npm test` still ran fifteen, so seven
    checks — the embedded scripts, the cover's floor, a PDF, a logo, a
    typeface and both generated stylesheets — existed and ran NOWHERE
    anyone would see before pushing. A green run locally meant nothing
    about the run that decides whether the site deploys.

    Compared rather than unified, because the two cannot be one list:
    CI runs each step separately so a failure says which one, installs
    poppler for the PDF, and splits across two jobs.
    """
    ci = [
        re.sub(r"\s*#.*$", "", step).strip()
        for step in re.findall(r"^\s*- run: (.+)$",
                               read(".github/workflows/deploy.yml"), re.M)
    ]
    # Not checks: one installs the dependencies, the other a system
    # package. Nothing to run locally for either.
    ci = [c for c in ci if not c.startswith(("npm ci", "sudo apt-get"))]

    said = re.search(r'"test":\s*"(.*?)"', read("package.json"))
    locally = [c.strip() for c in (said.group(1) if said else "").split("&&")]
    return [c for c in ci if c not in locally]


def duplicate_rules() -> "list[str]":
    """Selectors defined twice at the top level of the stylesheet.

    The file grew by appending blocks rather than editing the one
    already there, so `.case .image` ended up defined three times in
    three places — with `aspect-ratio` declared twice at different
    values — and the result was correct only because the last block
    happened to come last. Nothing was broken, which is the point: this
    is how an edit silently stops applying.

    Only TOP-LEVEL rules with a SINGLE selector. A rule inside a media
    query is a deliberate override; `a, b { }` is two things sharing one
    behaviour. Neither is this problem, and a check that cries wolf
    teaches you to ignore it.
    """
    css = re.sub(r"/\*.*?\*/", "", read("static/css/site.css"), flags=re.S)

    seen: "dict[str, int]" = {}
    dupes = []
    depth = 0
    head_start = 0

    for i, ch in enumerate(css):
        if ch == "{":
            if depth == 0:
                head = " ".join(css[head_start:i].split())
                # a sole selector, not a group, and not an at-rule
                if head and "," not in head and not head.startswith("@"):
                    line = css.count("\n", 0, i) + 1
                    if head in seen:
                        dupes.append(f"{head}  — lines {seen[head]} and {line}")
                    else:
                        seen[head] = line
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                head_start = i + 1

    return dupes


def main() -> int:
    problems = []
    dupes = duplicate_rules()
    unrun = unrun_checks()
    misplaced = print_rules_come_last()
    for name, rel, pattern, expected, why in INVARIANTS:
        found = len(re.findall(pattern, read(rel)))
        if found != expected:
            problems.append((name, rel, found, expected, why))

    if not problems and not dupes and not unrun and not misplaced:
        print(f"\n  invariants: {len(INVARIANTS)} hold, no selector defined "
              f"twice, and npm test runs what the workflow runs\n")
        return 0

    if misplaced:
        print("\n  THE STYLESHEET ENDS IN THE WRONG PLACE\n")
        for why in misplaced:
            print(f"    {why}\n")

    if unrun:
        print("\n  THE WORKFLOW RUNS CHECKS THAT npm test DOES NOT\n")
        for c in unrun:
            print(f"    {c}")
        print("      So a clean run here can still fail in CI. Add them to")
        print('      the "test" script in package.json.\n')

    if dupes:
        print("\n  THE SAME SELECTOR IS DEFINED TWICE\n")
        for d in dupes:
            print(f"    {d}")
        print("      The later one silently wins. Merge them, or this is")
        print("      how an edit stops applying and nobody can say why.\n")

    if not problems:
        return 1 if (dupes or unrun or misplaced) else 0

    print("\n  INVARIANT BROKEN\n")
    for name, rel, found, expected, why in problems:
        print(f"    {name}")
        print(f"      {rel}: found {found}, expected {expected}")
        print(f"      {why}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
