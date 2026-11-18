#!/usr/bin/env python3
"""Every change the panel is allowed to make, as verbs.

This was one file of 1141 lines. It is five, by what they know about:

    surgery.py   writing one value into a file without disturbing it
    words.py     the page's own sentences
    launch.py    identity, contact, colours, typeface, legal notice
    blocks.py    objects — adding, removing, changing a field
    drops.py     files someone drops: photographs, a film, a document,
                 the mark, the typeface

THE PATHS ARE NOT RE-EXPORTED HERE, ON PURPOSE.

`surgery.CONTENT`, `surgery.CONFIG` and `surgery.ROOT` are the only
copies. `tools/studio/check.py` points them at a temporary directory so
that nothing it does can touch the client's real content file — and
`from .surgery import CONTENT` here would hand every caller a second
copy that redirection would not reach. The check would then pass while
writing to the real file. So the paths are reached through the module
that owns them, always, and `check.py` asserts afterwards that the real
file was never touched.
"""
from . import surgery                                       # noqa: F401
from .surgery import MAX_LEN, UNWRITTEN, Refused, plain, quote  # noqa: F401
from .words import TEXT_FIELDS, set_text                    # noqa: F401
from .launch import CONFIG_FIELDS, set_config               # noqa: F401
from .blocks import (add, add_project, apply_edit, remove,  # noqa: F401
                     remove_project, write)
from .drops import (MAGIC, MAX_IMAGE, attach, attach_dossier,  # noqa: F401
                    attach_photo, attach_showreel, remove_dossier,
                    remove_font, remove_logo, remove_photo, remove_showreel,
                    set_font, set_logo)
