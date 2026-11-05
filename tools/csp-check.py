#!/usr/bin/env python3
"""The policy still describes the page it is attached to.

    python3 tools/csp-check.py        # after a build

`script-src` is the directive that decides whether an injected script
runs. It used to say `'unsafe-inline'`, which answers "yes, any of
them", in order to permit the one inline script this site actually has —
the boot script in templates/_head.html.

It now names that script by hash instead. A hash is strictly better and
has one real weakness: edit the script and forget the hash, and the
browser refuses it. That weakness is what this file removes.

WHY IT HASHES THE BUILT PAGE AND NOT THE TEMPLATE.

Because the browser hashes what it receives. `minify_html` rewrites the
markup on the way out, and a hash taken from the source would be a hash
of something nobody is served — correct in the repository and wrong in
the only place it is used. The same reasoning that made the smear filter
move out of the template: what the minifier does is part of the output.

WHAT IT CHECKS.

  * every inline script in every built page is named by that page's own
    policy
  * no `'unsafe-inline'` in script-src, in any page
  * no inline event handlers, which hashes cannot cover and which would
    therefore need `'unsafe-inline'` back
  * a page carrying an inline script has a policy at all

A page with nothing inline to protect is left alone — Zola's own 404 is
a title and a heading, and demanding a policy there would be noise that
teaches people to ignore the check.

The failure is quiet by nature — a stale hash breaks nothing visible in
the repository and everything in a browser — which is the kind of thing
that has to be a check rather than a habit.
"""

import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

# The minifier reorders attributes and drops quotes where it can, so
# `content` may come before `http-equiv` and `http-equiv` may be bare.
# Matching the tag first and its attributes second survives both — a
# regex written against the source order silently matched nothing.
META_TAG = re.compile(r"<meta\s[^>]*Content-Security-Policy[^>]*>", re.I)
CONTENT = re.compile(r'content=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I | re.S)
SCRIPT = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.S | re.I)
# `on…=` on an element. Deliberately not matched inside the policy text
# itself, which is why the page is searched for the attribute shape.
ON_ATTR = re.compile(r"<[^>]+\s(on[a-z]+)\s*=", re.I)


def sha256_of(text: str) -> str:
    return base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()


def main() -> int:
    if not PUBLIC.is_dir():
        print("\n  no public/ — run `zola build` first\n", file=sys.stderr)
        return 1

    pages = sorted(PUBLIC.rglob("*.html"))
    if not pages:
        print("\n  no pages in public/ — nothing to check\n", file=sys.stderr)
        return 1

    problems = []
    skipped: list[str] = []
    hashed = 0

    for page in pages:
        where = page.relative_to(PUBLIC)
        html = page.read_text(encoding="utf-8")

        bodies = [b for b in SCRIPT.findall(html) if b.strip()]

        tag = META_TAG.search(html)
        if not tag:
            # A page with nothing inline to protect needs no policy —
            # Zola's own 404 is markup and a title. A page WITH an
            # inline script and no policy is the regression worth
            # catching, because the hash would have nowhere to live.
            if bodies:
                problems.append(
                    f"{where}: has {len(bodies)} inline script(s) and no "
                    "Content-Security-Policy"
                )
            else:
                skipped.append(str(where))
            continue

        found = CONTENT.search(tag.group(0))
        policy = next((g for g in (found.groups() if found else ()) if g), "")

        script_src = ""
        for directive in policy.split(";"):
            name, _, rest = directive.strip().partition(" ")
            if name == "script-src":
                script_src = rest

        if "'unsafe-inline'" in script_src:
            problems.append(
                f"{where}: script-src still allows 'unsafe-inline' — the hash "
                "below is then decoration, because anything else runs too"
            )

        for handler in ON_ATTR.findall(html):
            problems.append(
                f"{where}: inline handler {handler}= — a hash cannot cover one, "
                "so this would need 'unsafe-inline' back"
            )

        for body in bodies:
            digest = f"'sha256-{sha256_of(body)}'"
            if digest in script_src:
                hashed += 1
            else:
                problems.append(
                    f"{where}: an inline script is not named by the policy.\n"
                    f"        the page serves {len(body)} bytes hashing to\n"
                    f"            {digest}\n"
                    "        put that in script-src in templates/_head.html"
                )

    if problems:
        print("\n  CONTENT SECURITY POLICY\n")
        for p in problems:
            print(f"    - {p}")
        print()
        return 1

    note = f", {len(skipped)} with nothing inline to protect" if skipped else ""
    print(f"\n  csp: {len(pages)} page(s), {hashed} inline script(s) named by "
          f"hash, no 'unsafe-inline'{note}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
