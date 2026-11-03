#!/usr/bin/env python3
"""Build the saveable contact card from config.toml.

    python3 tools/vcard.py

Writes static/contact.vcf when a verified address is configured, and
REMOVES it when one is not. Both halves matter: a stale card left behind
after someone cleared the address would be a published placeholder, which
is the thing the brief forbids (§4.08).

vCard 3.0 rather than 4.0 — 4.0 is the better spec and iOS and Android
are both happier with 3.0, which is the only test that counts here.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "contact.vcf"


# Reading TOML is shared — see tools/toml_read.py for why.
from toml_read import value  # noqa: E402


def escape(v: str) -> str:
    # Commas, semicolons and backslashes are field separators in vCard.
    # Unescaped, a name like "Smith, Jr." silently becomes two fields.
    return v.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,")


def main() -> int:
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")
    email = value(cfg, "email")

    if not email:
        if OUT.exists():
            OUT.unlink()
            print("\n  no address configured — removed the stale contact card\n")
        else:
            print("\n  no address configured — no contact card, as intended\n")
        return 0

    name = value(cfg, "vcard_name")
    if not name:
        print("\n  an address is set but vcard_name is empty — "
              "a card with no name on it is not a contact\n", file=sys.stderr)
        return 1

    # "Given Family" in, "Family;Given;;;" out. Anything with more than two
    # parts keeps the last as the family name and the rest as given.
    parts = name.split()
    family, given = parts[-1], " ".join(parts[:-1])

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{escape(family)};{escape(given)};;;",
        f"FN:{escape(name)}",
        f"EMAIL;TYPE=INTERNET,WORK:{escape(email)}",
    ]
    for key, fmt in (
        ("vcard_org",   "ORG:{}"),
        ("vcard_role",  "TITLE:{}"),
        ("vcard_phone", "TEL;TYPE=CELL,VOICE:{}"),
        ("vcard_url",   "URL:{}"),
    ):
        v = value(cfg, key)
        if v:
            lines.append(fmt.format(escape(v)))
    lines.append("END:VCARD")

    # CRLF is what the spec says, and what the stricter parsers insist on.
    OUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"\n  wrote {OUT.relative_to(ROOT)} for {name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
