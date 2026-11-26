#!/usr/bin/env python3
"""Versions of the site that are not the committed one.

Lifted out of `tools/render-check.py`. Several checks need a site that
does not exist in the repository — one with projects in a reference,
one with a project added and no photograph yet, one configured `live`.

Each is a COPY built beside the output, never inside it: `zola build -o
<out> -f` wipes the output directory first, so a source root nested in
it deletes itself on the way to being built.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
# A named spot, so check_named_spot has something to measure. The
# mechanism carrying these two numbers was dead for weeks.
look = "33 77"

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


def build_with_a_waiting_project(out: Path) -> Path:
    """A site where one project exists and has no photograph yet.

    The state the panel's "add a project" leaves behind, between
    pressing the button and dropping the first image. It used to STOP
    THE BUILD — `resize_image` was handed the empty path — and both
    `objects.py` and `content-check.py` called the page sound, so the
    first anyone knew was a failed deploy.
    """
    root = out.with_name(out.name + "-waiting")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name in ("content", "templates", "static"):
        shutil.copytree(ROOT / name, root / name,
                        ignore=shutil.ignore_patterns("processed_images"))
    shutil.copy2(ROOT / "config.toml", root / "config.toml")

    page = root / "content" / "_index.md"
    text = page.read_text(encoding="utf-8")
    waiting = ('[[extra.project]]\n'
               'id = "waiting-on-a-photograph"\n'
               'reference = 1\n'
               'name = "Added, not yet filled"\n\n')
    at = text.index("[[extra.project]]")
    page.write_text(text[:at] + waiting + text[at:], encoding="utf-8")
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


def build_with_two_faces(out: Path) -> Path:
    """A site whose headline carries two typefaces.

    The designer's direction is one sentence set in two faces, marked
    in the content with `((two parens))`. Nothing in the real content
    uses it yet — that is the point of the request, to leave the room
    without showing it — so the only way to check that a mixed headline
    still plays word by word is to make one.
    """
    root = out.with_name(out.name + "-two-faces")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name in ("content", "templates", "static"):
        shutil.copytree(ROOT / name, root / name,
                        ignore=shutil.ignore_patterns("processed_images"))
    shutil.copy2(ROOT / "config.toml", root / "config.toml")

    page = root / "content" / "_index.md"
    text = page.read_text(encoding="utf-8")
    found = re.search(r'(?m)^approach_title = "([^"]*)"', text)
    if not found:
        raise SystemExit("\n  no approach_title to mark up — look at "
                         "content/_index.md\n")
    words = found.group(1).split()
    if len(words) < 2:
        raise SystemExit("\n  the headline is too short to set part of it in "
                         "another face\n")
    # The LAST word, and the one before it left alone: that way the
    # check can tell a headline that was split from one that was not,
    # and a face that was carried from one that was dropped.
    words[-1] = f"(({words[-1]}))"
    page.write_text(
        text[:found.start()]
        + f'approach_title = "{" ".join(words)}"'
        + text[found.end():],
        encoding="utf-8")
    return root


def build_with_a_small_strip(out: Path) -> Path:
    """A site whose carousel copies are much smaller than the big ones.

    The stand-in photographs are 1000px, so the copy served in the
    strip and the bigger copy swapped in when a project opens come out
    the same size — and a page that reads a photograph's height from
    whatever has LOADED so far then looks correct, because both
    answers agree.

    They do not agree with real photography: 1000px in the strip,
    2000px when opened. This shrinks the strip's copy to 400px so the
    two differ here as well, which is the only way to see the
    difference in a check.
    """
    root = out.with_name(out.name + "-small-strip")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name in ("content", "templates", "static"):
        shutil.copytree(ROOT / name, root / name,
                        ignore=shutil.ignore_patterns("processed_images"))
    shutil.copy2(ROOT / "config.toml", root / "config.toml")

    page = root / "templates" / "index.html"
    small = 'resize_image(path="@/" ~ ph.file, width=1000, op="fit_width", format="webp", quality=74)'
    text = page.read_text(encoding="utf-8")
    if small not in text:
        raise SystemExit("\n  the carousel's copy is not made the way this "
                         "variant expects — look at templates/index.html\n")
    page.write_text(text.replace(small, small.replace("width=1000", "width=400")),
                    encoding="utf-8")
    return root
