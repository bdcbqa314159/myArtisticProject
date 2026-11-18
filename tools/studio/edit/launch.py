#!/usr/bin/env python3
"""The fields a launch needs: identity, contact, colours, legal notice.

Everything here is in `config.toml` rather than the content file, and
two of these sections are not text at all but decisions by someone
else: `[extra.theme]` is the graphiste's palette and typeface, and
writing it regenerates `static/css/theme.css` through the tool that
knows what may appear in a stylesheet. The panel never writes CSS.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from . import surgery as s


# The fields that decide a launch, and nothing else.
#
# An allowlist rather than "any key in config.toml": the file also holds
# `live`, the base URL and the build settings, and a panel that could
# reach those is a panel that can take the site down from a browser.
#
# `live` is deliberately absent. The gate decides whether the site MAY
# be published; a person decides whether it IS. That is not a button.
CONFIG_FIELDS = {
    "extra.real": {
        "name":          "the name on the page",
        "person":        "the person, as they write it",
        "title":         "the browser tab and the shared link",
        "approach_lead": "the paragraph under 01 / Approach",
        "about_lead":    "the opening of 06 / About",
    },
    "extra.contact": {
        "email":       "the verified business address — never a placeholder",
        "vcard_name":  "as it should appear in a phonebook",
        "vcard_role":  "the line under the name on a saved card",
        "vcard_org":   "the entity",
        "vcard_phone": "optional, international format",
        "vcard_url":   "optional",
    },
    # Only `url`. The mark filename and the service's name are the
    # studio's, and a mark pointing at a file that is not there is a
    # broken image in the footer — not a thing to expose to a browser.
    "extra.social.linkedin": {
        "url": "their LinkedIn profile, not linkedin.com",
    },
    "extra.social.whatsapp": {
        "url": "https://wa.me/ and the business number",
    },
    # The graphiste's decisions. Written into config.toml like any other
    # launch field, and `set_config` regenerates static/css/theme.css
    # afterwards — so the panel never writes CSS itself, it only ever
    # changes a value that a tool then validates and renders.
    "extra.theme": {
        "serif": 'the display face, e.g. "Canela, Georgia, serif"',
        "sans":  "everything else",
    },
    "extra.theme.cream": {
        "ink": "body text", "muted": "secondary text",
        "faint": "the quietest text", "line": "rules and borders",
        "bg": "the ground", "panel": "cards and unloaded images",
        "tint": "the faint fill behind a section",
        "accent": "buttons and anything emphatic",
    },
    "extra.theme.cool": {
        "ink": "body text", "muted": "secondary text",
        "faint": "the quietest text", "line": "rules and borders",
        "bg": "the ground", "panel": "cards and unloaded images",
        "tint": "the faint fill behind a section",
        "accent": "buttons and anything emphatic",
    },
    "extra.legal": {
        "entity":       "the legal name of the publisher",
        "status":       "e.g. Entrepreneur individuel, SASU",
        "registration": "SIRET / RCS",
        "address":      "the registered address",
        "publisher":    "directeur de la publication",
    },
}


def _regenerate_theme() -> str:
    """Render static/css/theme.css from what config.toml now says.

    The panel does not write CSS. It writes a value, and this asks the
    tool that knows how to validate one to produce the stylesheet — so
    there is exactly one place that decides what may appear in it.
    """
    import subprocess
    out = subprocess.run([sys.executable, str(s.ROOT / "tools" / "theme.py")],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        return (out.stderr or out.stdout or "the theme could not be written"
                ).strip().splitlines()[-1].strip()
    return ""


def set_config(section: str, key: str, value: str) -> str:
    """Change one launch field in config.toml.

    Surgical, for the same reason as the content file: config.toml is
    mostly s.comments explaining why each switch exists — the identity
    swap, why `live` is false, why French is not built. A serializer
    would take all of it.
    """
    if section not in CONFIG_FIELDS:
        raise s.Refused(f"{section} is not editable here")
    if key not in CONFIG_FIELDS[section]:
        raise s.Refused(f"{section} has no editable field {key!r}")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise s.Refused("a value is one line")
    if len(value) > s.MAX_LEN:
        raise s.Refused(f"{len(value)} characters; the limit is {s.MAX_LEN}")
    s.plain(value)

    text = s.CONFIG.read_text(encoding="utf-8")

    header = re.search(rf"^\[{re.escape(section)}\]\s*$", text, re.M)
    if not header:
        raise s.Refused(f"config.toml has no [{section}]")
    start = header.end()
    nxt = re.search(r"^\[", text[start:], re.M)
    end = start + (nxt.start() if nxt else len(text[start:]))
    block = text[start:end]

    # The trailing comment is kept. In config.toml it is often the only
    # thing saying what the field is for — "never a placeholder",
    # "international format" — and replacing the line without it would
    # quietly delete the instruction along with the blank.
    line = re.search(
        rf'^({re.escape(key)}\s*=\s*)"(?:[^"\\]|\\.)*"([ \t]*#.*)?$', block, re.M
    )
    if not line:
        raise s.Refused(f"[{section}] has no {key} line")

    updated = (
        block[: line.start()]
        + f'{line.group(1)}"{s.quote(value)}"{line.group(2) or ""}'
        + block[line.end():]
    )
    candidate = text[:start] + updated + text[end:]

    original = text
    s.put(s.CONFIG, candidate)
    try:
        if s.comments(candidate) < s.comments(original):
            raise s.Refused("a comment was lost; the edit was undone")
        leaked = s.protected_terms_leaked()
        if leaked:
            raise s.Refused(
                f"{leaked} is protected from this repository — it is public. "
                "See NOTICE; the real identity goes in at handover."
            )
    except Exception:
        s.put(s.CONFIG, original)
        raise

    if section.startswith("extra.theme"):
        # The value is written; now the stylesheet it decides. If the
        # tool refuses it, s.put the config back — a theme half applied
        # is a page whose colours disagree with the file that chose
        # them.
        wrong = _regenerate_theme()
        if wrong:
            s.put(s.CONFIG, original)
            raise s.Refused(wrong)
        return f"[{section}] {key} updated — the stylesheet was rewritten"

    return f"[{section}] {key} updated"
