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
            "look":      (False, 'where the light sits on this print, as "x y" '
                                 'percentages of it — e.g. "50 100" for the '
                                 'foot. Leave empty for the arrangement\'s own '
                                 'place, which is already clear of its neighbours'),
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
    "dossier": (
        "extra.dossier",
        "A document behind one concept, shown as pages and never as a "
        "file. The PDF itself is not published: `tools/dossier.py` turns "
        "it into images here, so there is nothing on the server to "
        "download and nothing executable to serve. `pages` is how many "
        "`dossier-<id>-pNN.jpg` there are in content/.",
        {
            "concept": (True, "which concept it belongs to, 1-based"),
            "id":      (True, "lower-case name used for the files, e.g. format-two"),
            "pages":   (True, "how many pages — must match the files in content/"),
            "alt":     (True, "what the document is, for someone who cannot see it"),
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
# A dossier id becomes part of a filename, so it is held to the same
# shape `tools/dossier.py` enforces when it writes them.
DOSSIER_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")

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
MAY_BE_EMPTY = {"project", "photo", "dossier"}


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
            # "x y", both 0-100. A light at 300% is a light nobody
            # will find, and the template would set it without a word.
            spot = obj.get("look", "").strip()
            if spot:
                bits = spot.split()
                ok = len(bits) == 2 and all(
                    b.replace(".", "", 1).isdigit() and 0 <= float(b) <= 100
                    for b in bits)
                if not ok:
                    problems.append(
                        f"{where}: look is {spot!r} — it wants two numbers "
                        'between 0 and 100, like "50 100"')

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

    # THE CAPS. Five projects on a fridge and five photographs in a
    # project — fewer is fine, more is not. The patchwork shows one
    # large and four over it, so a sixth project would be a project the
    # page silently does not mention, which is worse than a build that
    # stops and says so.
    from collections import Counter
    per_ref = Counter(p.get("reference", "") for p in projects)
    for ref, many in sorted(per_ref.items()):
        if many > 5:
            problems.append(
                f"reference {ref}: {many} projects, and a patchwork shows "
                "five — the rest would be on no page"
            )

    per_project = Counter(s.get("project", "") for s in blocks(fm, "extra.photo"))
    for owner, many in sorted(per_project.items()):
        if many > 5:
            problems.append(
                f"project {owner}: {many} photographs, and a carousel takes "
                "five"
            )

    # ---- dossiers ------------------------------------------------------
    #
    # A dossier is the one object whose files are DERIVED rather than
    # named: the page images come out of `tools/dossier.py`, and the
    # count in the front matter has to agree with what is on disk. If it
    # does not, the page either stops short of the document or shows a
    # gap where a page should be, and neither announces itself.
    concepts = blocks(fm, "extra.concepts")
    dossiers = blocks(fm, "extra.dossier")
    claimed = {}
    for i, doc in enumerate(dossiers, 1):
        slug = doc.get("id", "").strip()
        where = doc.get("concept", "").strip()

        if where:
            if not where.isdigit() or not 1 <= int(where) <= len(concepts):
                problems.append(
                    f"dossier {i} ({slug or '?'}): concept {where!r} is not "
                    f"one of the {len(concepts)} there are"
                )
            elif where in claimed:
                problems.append(
                    f"dossier {i} ({slug or '?'}): concept {where} already has "
                    f"a document, {claimed[where]!r}. A card shows one"
                )
            else:
                claimed[where] = slug

        if not slug:
            continue
        if not DOSSIER_ID.match(slug):
            problems.append(
                f"dossier {i} ({slug!r}): not a usable id — lower case "
                f"letters, digits and hyphens only. It becomes a filename"
            )
            continue

        said = doc.get("pages", "").strip()
        on_disk = sorted(CONTENT.parent.glob(f"dossier-{slug}-p*.jpg"))
        if not said.isdigit():
            problems.append(f"dossier {i} ({slug}): pages is {said!r}, which "
                            f"is not a number")
        elif int(said) != len(on_disk):
            problems.append(
                f"dossier {i} ({slug}): says {said} pages, and content/ has "
                f"{len(on_disk)}. Re-run tools/dossier.py, or the page shows "
                f"a gap where a page should be"
            )

        # The PDF must not be sitting in content/ — Zola copies that
        # directory into the built site wholesale, which would publish
        # the very file the reader is not meant to be able to take.
        stray = list(CONTENT.parent.glob("*.pdf"))
        if stray:
            problems.append(
                f"content/ holds {stray[0].name}. Everything in content/ is "
                f"copied into the built site, so that PDF would be "
                f"downloadable — which is the one thing a dossier is for "
                f"avoiding"
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
