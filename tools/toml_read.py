#!/usr/bin/env python3
"""Reading values out of TOML, in one place.

Python 3.9 has no `tomllib`, and adding a dependency for four small
tools would be worse than this. What was worse still was four tools each
writing their own regex: they agreed with each other only by
coincidence, and a change to one left the others reading the file
differently.
"""

import re
from pathlib import Path


def value(text: str, key: str) -> str:
    """The first `key = "…"` in `text`, stripped. Empty if absent."""
    m = re.search(rf'^{re.escape(key)}\s*=\s*"([^"]*)"', text, re.M)
    return m.group(1).strip() if m else ""


def flag(text: str, key: str) -> bool:
    """`key = true`, as a boolean. Anything else, including absent, is False."""
    return re.search(rf"^{re.escape(key)}\s*=\s*true\s*$", text, re.M) is not None


def front_matter(path: Path) -> str:
    """The TOML between the +++ fences. Empty if there are none."""
    parts = path.read_text(encoding="utf-8").split("+++")
    return parts[1] if len(parts) >= 3 else ""
