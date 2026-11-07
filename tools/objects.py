#!/usr/bin/env python3
"""The content objects: what they are, what they must carry, and how to add one.

    python3 tools/objects.py            # check every object in content/
    python3 tools/objects.py --add reference
    python3 tools/objects.py --docs     # regenerate OBJECTS.md

The page is assembled from objects. Adding a project, a capability or a
concept is dropping a block into content/_index.md — no template is
touched, nothing is positioned by hand, and the section it belongs to
grows by itself.

THIS FILE IS THE ONLY DEFINITION. The checker, the scaffolder and
OBJECTS.md are all generated from the table below, so the documentation
cannot drift from what is enforced — which is the usual way a handover
document becomes a lie.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "_index.md"
DOCS = ROOT / "OBJECTS.md"


# name: (toml array, what it is, {field: (required?, what it is)})
SCHEMA = {
    "reference": (
        "extra.work",
        "One organisation worked with, and the role held there. The six of "
        "them are ordered by widening discipline, and the order is the "
        "argument: a practice developing, not six credentials side by side.",
        {
            "name":        (True,  "the organisation, as it writes its own name"),
            "domain":      (True,  'the territory, as "A × B" — Sport × Culture'),
            "text":        (True,  "one sentence on what the work was"),
            "role":        (True,  "the role held, exactly. Never rounded up"),
            "verified":    (True,  "true only once the role has been checked against the record"),
            "verified_on": (False, "the day it was checked, YYYY-MM-DD. Required when verified"),
            "evidence":    (False, "what it was checked against. Required when verified"),
            "image":       (False, "a file in content/, e.g. project-01.jpg"),
            "alt":         (False, "what the photograph shows, for someone who cannot see it. Required when there is an image"),
        },
    ),
    "capability": (
        "extra.services",
        "One way of working together. Read as a group, so they should be "
        "the same size as each other.",
        {
            "name": (True, "the capability, three or four words"),
            "text": (True, "one sentence. No claim the rest of the page does not support"),
        },
    ),
    "concept": (
        "extra.concepts",
        "An original format. NOT a completed commission, and the status is "
        "what keeps that distinction visible.",
        {
            "status": (True, 'where it stands — "In development", "Opportunity area"'),
            "name":   (True, "the format's name"),
            "text":   (True, "one sentence on what it is"),
        },
    ),
    "project": (
        "extra.project",
        "One body of work inside a reference — the client's \"tiny "
        "portfolio\". A reference shows several of these as thumbnails; "
        "opening one gives its photographs.",
        {
            "id":        (True, 'unique, and what a photograph points at — e.g. "r1-a"'),
            "reference": (True, "which of the six references this belongs to, 1-6"),
            "name":      (True, "the project, as it is shown under its thumbnail"),
        },
    ),
    "photo": (
        "extra.photo",
        "One photograph inside a project. The FIRST of a project is also "
        "its thumbnail — there is no separate cover field, because a cover "
        "is a second thing to keep in step with the first and the first to "
        "go stale.",
        {
            "project": (True, "the id of the project it belongs to"),
            "file":    (True, "a file in content/, e.g. r1-a-01.jpg"),
            "alt":     (True, "what it shows, for someone who cannot see it"),
        },
    ),
    "pillar": (
        "extra.about_pillars",
        "One strand of the practice, in About.",
        {
            "name": (True, "the strand"),
            "text": (True, "a phrase, not a sentence — these sit in a narrow column"),
        },
    ),
}


# Fields the studio panel must never write.
#
# `verified` and its two companions are a RECORD, not content: a role is
# verified by checking it against something, which is an act that happens
# away from a screen. A box that could be ticked in a browser would make
# the gate meaningless — the one check standing between an unverified
# claim and a published page.
#
# `image` is locked here because slice 4 owns it: a photograph arrives
# with a file and an `alt`, and adding one without the other is the gap
# the alt field was introduced to close.
LOCKED = {"verified", "verified_on", "evidence", "image"}

# Kinds that are allowed to have none.
#
# Every other class is required to exist: stripping the page to its front
# matter once produced "0 reference, 0 capability — all well formed",
# which is a check reporting success at the moment the page emptied.
#
# Projects and photographs are different. They are additive, the tracked
# page carries no real ones, and a site with six references and no
# projects yet is a site mid-handover rather than a broken one.
MAY_BE_EMPTY = {"project", "photo"}


def front_matter() -> str:
    parts = CONTENT.read_text(encoding="utf-8").split("+++")
    return parts[1] if len(parts) >= 3 else ""


def blocks(fm: str, array: str):
    """Every [[array]] block, as a list of {field: raw value}."""
    found = []
    for body in re.findall(rf"\[\[{re.escape(array)}\]\](.*?)(?=\n\[\[|\n# ----|\Z)", fm, re.S):
        fields = {}
        for line in body.splitlines():
            m = re.match(r'\s*([a-z_]+)\s*=\s*(.*?)\s*$', line)
            if m:
                fields[m.group(1)] = m.group(2).strip('"')
        found.append(fields)
    return found


def check() -> int:
    fm = front_matter()
    problems = []

    for kind, (array, _doc, fields) in SCHEMA.items():
        for i, obj in enumerate(blocks(fm, array), 1):
            # Whatever this kind calls itself. A photograph has no
            # `name`, so the label was "photo 1 (?)" — a message that
            # tells you something is wrong and not which thing.
            label = obj.get("name") or obj.get("file") or obj.get("id") or "?"
            where = f"{kind} {i} ({label})"

            for field, (required, _) in fields.items():
                if required and not obj.get(field, "").strip():
                    problems.append(f"{where}: {field} is required and empty")

            # A misspelt field is silently ignored by the template, which
            # is the worst failure available: the page looks fine and the
            # value is simply absent.
            for field in obj:
                if field not in fields:
                    problems.append(
                        f"{where}: unknown field {field!r} — it will be ignored"
                    )

            # Conditionals the flat table cannot express.
            if obj.get("image") and not obj.get("alt", "").strip():
                problems.append(
                    f"{where}: has an image and no alt. A photograph with no "
                    "description is the case the requirement exists for"
                )
            if obj.get("verified") == "true":
                for field in ("verified_on", "evidence"):
                    if not obj.get(field, "").strip():
                        problems.append(f"{where}: verified but no {field}")

    # An empty class is not "well formed", it is missing. Stripping
    # content/_index.md to its front matter produced "0 reference, 0
    # capability, 0 concept, 0 pillar — all well formed", which is a
    # check reporting success at the moment the page became empty.
    for kind, (array, _doc, _fields) in SCHEMA.items():
        if kind in MAY_BE_EMPTY:
            continue
        if not blocks(fm, array):
            problems.append(f"no {kind} objects at all — [[{array}]] is empty")

    # --- what one object says about another ------------------------------
    # The flat model relates projects to references and photographs to
    # projects BY NAME. That is what keeps the checker and the studio
    # panel working on three levels without either learning to nest — and
    # the price of naming things is that a name can be wrong. These are
    # that price, paid here rather than by a reader finding an empty
    # gallery.
    projects = blocks(fm, "extra.project")
    references = blocks(fm, "extra.work")

    seen = {}
    for i, project in enumerate(projects, 1):
        name = project.get("id", "").strip()
        if name and name in seen:
            problems.append(
                f"project {i} ({name}): two projects share the id {name!r} — "
                f"the other is project {seen[name]}. Every photograph naming "
                "it would land in both"
            )
        elif name:
            seen[name] = i

        where = project.get("reference", "").strip()
        if where:
            if not where.isdigit() or not 1 <= int(where) <= len(references):
                problems.append(
                    f"project {i} ({name or '?'}): reference {where!r} is not "
                    f"one of the {len(references)} there are"
                )

    for i, photo in enumerate(blocks(fm, "extra.photo"), 1):
        owner = photo.get("project", "").strip()
        if owner and owner not in seen:
            problems.append(
                f"photo {i} ({photo.get('file', '?')}): no project has the id "
                f"{owner!r}, so this photograph is on no page"
            )

    if problems:
        print("\n  CONTENT OBJECTS\n")
        for p in problems:
            print(f"    - {p}")
        print()
        return 1

    counts = ", ".join(
        f"{len(blocks(fm, a))} {k}" for k, (a, _, _) in SCHEMA.items()
    )
    print(f"\n  objects: {counts} — all well formed\n")
    return 0


def add(kind: str) -> int:
    if kind not in SCHEMA:
        print(f"\n  no such object: {kind}", file=sys.stderr)
        print(f"  try: {', '.join(SCHEMA)}\n", file=sys.stderr)
        return 1
    array, _doc, fields = SCHEMA[kind]
    print(f"\nPaste into content/_index.md, under the other {kind} blocks:\n")
    print(f"[[{array}]]")
    for field, (required, what) in fields.items():
        value = "false" if field == "verified" else '""'
        mark = "" if required else "    # optional"
        print(f"{field} = {value}{mark}  # {what}" if mark else f'{field} = {value}  # {what}')
    print()
    return 0


def docs() -> int:
    out = [
        "# The content objects",
        "",
        "The page is assembled from objects. To add a project, a capability or",
        "a concept, drop a block into `content/_index.md` — no template is",
        "touched, nothing is positioned by hand, and the section grows by",
        "itself.",
        "",
        "```sh",
        "python3 tools/objects.py --add reference   # prints a block to paste",
        "python3 tools/objects.py                   # checks every object",
        "```",
        "",
        "Both run in CI. A required field left empty, or a field name",
        "misspelt, fails the build — a misspelt field is otherwise ignored in",
        "silence, which is the worst failure available: the page looks fine",
        "and the value is simply gone.",
        "",
        "**Generated from `tools/objects.py`. Do not edit by hand.**",
        "",
    ]
    for kind, (array, doc, fields) in SCHEMA.items():
        out += [f"## {kind}", "", f"`[[{array}]]` — {doc}", "",
                "| field | required | |", "|---|---|---|"]
        for field, (required, what) in fields.items():
            out.append(f"| `{field}` | {'yes' if required else 'no'} | {what} |")
        out.append("")
    DOCS.write_text("\n".join(out), encoding="utf-8")
    print(f"\n  wrote {DOCS.name}\n")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--docs" in args:
        sys.exit(docs())
    if "--add" in args:
        i = args.index("--add")
        sys.exit(add(args[i + 1] if i + 1 < len(args) else ""))
    sys.exit(check())
