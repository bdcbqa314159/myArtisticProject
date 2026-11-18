#!/usr/bin/env python3
"""The page's own sentences.

What `TEXT_FIELDS` allows is the whole of what the panel may reword,
and it is an allowlist because the alternative is a text box that can
write anything into a line of TOML. It fell a long way behind the page
once — the contact form arrived with seventeen sentences and not one
was added — so `tools/studio/check.py` compares it against what the
template renders, and against what can actually be clicked.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from . import surgery as s


# The page's own words — the titles and leads in content/_index.md's
# [extra] block. An allowlist rather than "any key in the file", for the
# same reason CONFIG_FIELDS is one: that block also holds `video`,
# `poster`, `nav` and `ecosystem_fields`, and a panel that could reach
# those is a panel that can point the page at a film that is not there
# or empty the navigation.
#
# Nothing wrote these before. The panel could edit objects and the
# launch fields and not one of the sentences a visitor actually reads,
# which is most of why it felt like a form rather than the site.
TEXT_FIELDS = {
    "eyebrow":          "the line above the name",
    "roles":            "the lead under the name",
    "intro":            "the paragraph under that",
    "cta_work":         "the first button",
    "cta_contact":      "the second button",
    "approach_title":   "the heading of 01 / Approach",
    "showreel_label":   "the word on the empty showreel slot",
    "showreel_spec":    "the line under it",
    "services_title":   "the heading of 02 / Expertise",
    "work_title":       "the heading of 03 / Selected Work",
    "work_lead":        "the paragraph under it",
    "work_note":        "the note under the references",
    "concepts_title":   "the heading of 04 / Concepts",
    "concepts_lead":    "the paragraph under it",
    "ecosystem_lead":   "the paragraph in 05 / Ecosystem",
    "about_title":      "the heading of 06 / About",
    "about_text":       "the second paragraph of About",
    "contact_title":    "the heading of 07 / Contact",
    "contact_lead":     "the paragraph under it",
    "form_title":       "the heading inside the form",
    "form_lead":        "the line under it",
    "form_mail":        "the label on the address field",
    "form_subject":     "the label on the subject field",
    "form_message":     "the label on the message field",
    "form_send":        "the button that sends",
    "form_cancel":      "the button that does not",
    "form_privacy":     "what happens to a message, in one sentence",

    # ---- the masthead ---------------------------------------------------
    "issue":            "the issue line in the masthead",
    "place":            "the places beside it",

    # ---- the two contact buttons ----------------------------------------
    "contact_copy":     "the button that copies an introduction",
    "contact_save":     "the button that saves a contact card",

    # ---- what the form says back ----------------------------------------
    #
    # Added late, and the reason is worth keeping. The form arrived long
    # after this allowlist was written, and its thirteen replies were
    # never added to it — so the one part of the page that talks back to
    # a visitor was the one part nobody could reword, in either
    # language. They are prose like everything else above.
    "form_sending":        "while a message is going",
    "form_sent":           "when it has gone",
    "form_failed":         "when it has not",
    "form_offline":        "when there is nowhere to send it yet",
    "err_mail_missing":    "no address given",
    "err_mail_invalid":    "an address that is not one",
    "err_mail_long":       "an address longer than an address can be",
    "err_mail_one":        "more than one address",
    "err_subject":         "a subject that cannot be sent",
    "err_message_missing": "no message given",
    "err_message_long":    "a message past the limit",
    "err_message_bad":     "a message that cannot be sent",
    "err_message_links":   "too many links in a message",
}


def set_text(key: str, value: str) -> str:
    """One of the page's own sentences, in content/_index.md.

    Surgical, like every other writer here: the file is mostly s.comments
    explaining why each decision was made — the voice rule, the ordering
    of the references — and a serialiser would take all of them.
    """
    if key not in TEXT_FIELDS:
        raise s.Refused(f"{key!r} is not editable here")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise s.Refused("a value is one line")
    if len(value) > s.MAX_LEN:
        raise s.Refused(f"{len(value)} characters; the limit is {s.MAX_LEN}")
    s.plain(value)
    if not value:
        raise s.Refused("that would leave it empty — remove the field instead")

    leak = s.protected_terms_leaked()
    if leak:
        raise s.Refused(leak)

    return s.write_front_field(key, value)
