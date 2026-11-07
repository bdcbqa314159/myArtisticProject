#!/usr/bin/env python3
"""The French page has the same shape as the English one.

    python3 tools/fr-check.py              # what has drifted, and what is untranslated
    python3 tools/fr-check.py --scaffold   # rebuild content/_index.fr.md from the English
    python3 tools/fr-check.py --source     # print each untranslated field with its English

WHY THIS EXISTS.

`content/_index.fr.md` was a stub from before the eight sections existed
— three fields the site no longer has, thirty-six it does. Nothing
compared the two files, so it fell that far behind without anyone
noticing, and the only reason it did no harm is that French was switched
off in `config.toml`.

Switching a thing off is not the same as fixing it. The field-by-field
comparison below is what makes falling behind impossible rather than
merely unlucky: add a field to the English page and this fails until the
French page has it too.

WHAT TRANSLATION MEANS HERE.

A French string is **translated** when it is neither empty nor still the
placeholder. Nothing here decides whether it is any GOOD — that is a
judgement, and the person who makes it reads French. The tool's job is
to make sure nothing is missing and nothing is silently English.

`--scaffold` rebuilds the French file from the English one, carrying
over every translation already made. Values that cannot be translated —
a filename, a verification record, a fragment link — are copied rather
than blanked, because translating them would break the page.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / "content" / "_index.md"
FR = ROOT / "content" / "_index.fr.md"

PLACEHOLDER = "À traduire"

# Values that are not prose. A filename translated is a filename broken;
# a verification record translated is a record falsified.
COPIED = {
    "image", "video", "poster",
    "verified", "verified_on", "evidence",
    "template", "draft",
    "href",          # a fragment link. Translated, it points nowhere.
}

# The brand is a trademark, not a word. It is the same in every language
# and must never be sent anywhere that might improve it.
BRAND_FIELDS = {"title"}


def front_matter(path: Path) -> str:
    parts = path.read_text(encoding="utf-8").split("+++")
    return parts[1] if len(parts) >= 3 else ""


def quoted(raw: str) -> "str | None":
    """The string inside a scalar assignment, or None if it is not one."""
    found = re.match(r'"((?:[^"\\]|\\.)*)"\s*(?:#.*)?$', raw)
    return found.group(1) if found else None


def assignments(fm: str):
    """Every assignment, with its COMPLETE value — lists included.

    Line-by-line is not enough and the first version of this file proved
    it: `nav`, `ecosystem_fields` and `ecosystem_title` span several
    lines or hold several strings, so they fell through as "not a
    string" and were copied from the English in silence. Thirteen
    visible strings reported as done. A checker that cannot see a third
    of the page is worse than none, because it is believed.

    So a value runs until its brackets balance.
    """
    array = ""
    index = -1
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        table = re.match(r"\s*\[\[([a-z_.]+)\]\]\s*$", line)
        if table:
            if table.group(1) != array:
                array, index = table.group(1), 0
            else:
                index += 1
            i += 1
            continue

        assign = re.match(r'\s*([a-z_]+)\s*=\s*(.*)$', line)
        if not assign:
            i += 1
            continue

        name, raw = assign.group(1), assign.group(2)
        depth = raw.count("[") - raw.count("]")
        start = i
        while depth > 0 and i + 1 < len(lines):
            i += 1
            raw += "\n" + lines[i]
            depth += lines[i].count("[") - lines[i].count("]")

        key = f"{array}[{index}].{name}" if array else name
        yield key, name, raw.strip(), start, i
        i += 1


# A quoted string, optionally introduced by `key =` as in an inline
# table. The key is what says whether it is prose or plumbing.
STRING = re.compile(r'(?:([a-z_]+)\s*=\s*)?"((?:[^"\\]|\\.)*)"')


def strings_in(raw: str):
    """Each quoted string in a value, with the key that introduced it."""
    for found in STRING.finditer(raw):
        yield found.group(1), found.group(2), found


def is_list(raw: str) -> bool:
    return raw.lstrip().startswith("[")


TABLE = re.compile(r"\{[^}]*\}")


def list_entries(key: str, name: str, raw: str):
    """Each string in a list, with a stable key.

    Two shapes, and they index differently. A list of inline tables —
    `nav` — is indexed by TABLE, so `label` and `href` of the same entry
    share a number. Counting strings instead put entry 0's href under
    `nav[1]`, which is the sort of off-by-one that makes a carried-over
    translation land on the wrong line.
    """
    if "{" in raw:
        for n, group in enumerate(TABLE.findall(raw)):
            for inner, text, _m in strings_in(group):
                yield f"{key}[{n}].{inner}", (inner or name), text
    else:
        for n, (_inner, text, _m) in enumerate(strings_in(raw)):
            yield f"{key}[{n}]", name, text


def fields(fm: str) -> "dict[str, tuple[str, str]]":
    """Flat map of every string on the page: key -> (field name, text).

    A list becomes one entry per string it holds — `nav[3].label`,
    `ecosystem_fields[0]` — because a list whose fourth label is still
    English is not "a field that exists", it is a field that is wrong.
    """
    out: "dict[str, tuple[str, str]]" = {}
    for key, name, raw, _a, _b in assignments(fm):
        if is_list(raw):
            for sub, inner, text in list_entries(key, name, raw):
                out[sub] = (inner, text)
            continue
        scalar = quoted(raw)
        if scalar is not None:
            out[key] = (name, scalar)
    return out


def rebuild_list(key: str, name: str, raw: str, pick) -> str:
    """The same list, with each string replaced by `pick`."""
    if "{" in raw:
        groups = iter(range(len(TABLE.findall(raw))))

        def one(match: "re.Match[str]") -> str:
            n = next(groups)
            return STRING.sub(
                lambda m: (f"{m.group(1)} = " if m.group(1) else "")
                + '"' + pick(f"{key}[{n}].{m.group(1)}", m.group(1) or name,
                             m.group(2)) + '"',
                match.group(0))

        return TABLE.sub(one, raw)

    counter = iter(range(len(list(strings_in(raw)))))
    return STRING.sub(
        lambda m: '"' + pick(f"{key}[{next(counter)}]", name, m.group(2)) + '"',
        raw)


def translatable(name: str, raw: str) -> bool:
    if name in COPIED or name in BRAND_FIELDS:
        return False
    return quoted(raw) is not None


def scaffold() -> int:
    """Rebuild the French file from the English one, keeping what exists.

    The English file is the template, so the French page cannot have a
    different shape — not "should not", cannot. Every translation
    already made is carried across by key.
    """
    parts = EN.read_text(encoding="utf-8").split("+++")
    if len(parts) < 3:
        print("\n  the English page has no front matter\n", file=sys.stderr)
        return 1

    existing = fields(front_matter(FR)) if FR.exists() else {}
    kept = {"n": 0}

    def pick(key: str, name: str, english: str) -> str:
        if name in COPIED or name in BRAND_FIELDS:
            return english
        was = existing.get(key)
        if was and was[1] not in ("", PLACEHOLDER):
            # Carried over even when it reads exactly as the English
            # does: "France · International" is correct French, and a
            # scaffold that blanked it would destroy a good translation
            # every time it ran. Whether an identical value is right is
            # a judgement, so the CHECK reports it and a person decides.
            kept["n"] += 1
            return was[1]
        return PLACEHOLDER

    header = (
        "\n"
        "# LA PAGE, EN FRANÇAIS.\n"
        "#\n"
        "# Rebuilt from content/_index.md by `tools/fr-check.py --scaffold`,\n"
        "# which is also what checks that the two files still have the same\n"
        "# fields. Do not add a field here by hand: add it to the English\n"
        "# page and run the scaffold, or the check reports a page that has\n"
        "# drifted — which is how this file fell thirty-six fields behind\n"
        "# the last time, unnoticed.\n"
        "#\n"
        '# A value still reading "À traduire" has not been translated.\n'
        "# `draft` below is managed by the scaffold: while anything is\n"
        "# untranslated the page is a draft, and Zola does not build it.\n"
        "#\n"
        "# Filenames, fragment links, verification records and the brand\n"
        "# are copied rather than translated — translating them breaks the\n"
        "# page or falsifies the record.\n"
        "\n"
    )

    out: "list[str]" = []
    skip_until = -1
    lines = parts[1].splitlines()
    spans = {a: (key, name, raw, b)
             for key, name, raw, a, b in assignments(parts[1])}

    for i, line in enumerate(lines):
        if i <= skip_until:
            continue
        if i in spans:
            key, name, raw, end = spans[i]
            skip_until = end
            if is_list(raw):
                out.append(f"{name} = {rebuild_list(key, name, raw, pick)}")
            elif quoted(raw) is not None:
                out.append(f'{name} = "{pick(key, name, quoted(raw))}"')
            else:
                out.append(f"{name} = {raw}")
            continue
        # The English file's prose comments explain the English copy.
        # Carried over they would be duplicated text free to disagree
        # with its original; the labelled dividers are kept because they
        # are structure rather than prose.
        if re.match(r"\s*#", line) and not re.match(r"\s*# ---- \S", line):
            continue
        out.append(line)

    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()

    after = fields(body)
    todo = [k for k, (n, v) in after.items()
            if v == PLACEHOLDER or (n not in COPIED and n not in BRAND_FIELDS and not v)]

    # Zola's own switch, kept honest by this script rather than by
    # anyone remembering. An untranslated page that builds is exactly
    # the failure that made French get switched off in the first place.
    draft = "\ndraft = true    # géré par tools/fr-check.py\n" if todo else ""

    FR.write_text(f"+++{header}{body}\n{draft}+++\n", encoding="utf-8")
    print(f"\n  wrote {FR.relative_to(ROOT)} — {len(after)} field(s), "
          f"{kept['n']} translation(s) kept, {len(todo)} still to translate")
    print(f"  {'draft: French is not built while any remain' if todo else 'complete — draft removed'}\n")
    return 0


def main(argv: "list[str]") -> int:
    if "--scaffold" in argv:
        return scaffold()

    if not FR.exists():
        print("\n  no French page — run: python3 tools/fr-check.py --scaffold\n")
        return 1

    en = fields(front_matter(EN))
    fr = fields(front_matter(FR))

    missing = [k for k in en if k not in fr]
    extra = [k for k in fr if k not in en]

    if missing or extra:
        print("\n  THE FRENCH PAGE HAS DRIFTED\n")
        for k in missing:
            print(f"    - missing: {k}")
        for k in extra:
            print(f"    - no longer in the English page: {k}")
        print("\n    python3 tools/fr-check.py --scaffold\n")
        return 1

    todo = [k for k, (_n, v) in fr.items() if v == PLACEHOLDER]

    # Still reading as the English does. Legitimate for a proper noun and
    # a mistake everywhere else, so it is reported rather than failed —
    # the person who can tell the difference reads French.
    english = [
        k for k, (n, v) in fr.items()
        if v and v != PLACEHOLDER and n not in COPIED and n not in BRAND_FIELDS
        and v == en[k][1]
    ]

    if "--source" in argv:
        print()
        for k in todo:
            print(f"    {k}\n      en: {en[k][1]}\n")
        return 0

    note = f", {len(english)} identical to the English" if english else ""
    print(f"\n  french: {len(fr)} field(s), same shape as the English page — "
          f"{len(todo)} still to translate{note}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
