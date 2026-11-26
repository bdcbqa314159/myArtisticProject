#!/usr/bin/env python3
"""The one rule about what a text value may contain.

    from markers import trouble

TWO FACES IN ONE SENTENCE. The client's designer is going towards a
headline carrying two typefaces, so a field may mark a stretch of itself
with `((like this))` and the template turns it into one span. The page
reads that span back when it splits a headline into words, so a mixed
line keeps its word-by-word entrance.

WHY THIS FILE EXISTS RATHER THAN A FILTER IN THE TEMPLATE. The obvious
way — escape the value, insert the span, mark it safe — does not work,
and that was measured rather than assumed: this Tera escapes the span
the template itself inserted, so the page shows the tag as text. Taking
the `escape` out makes the span live and leaves whatever was typed
unescaped along with it.

So the value is made safe BEFORE it is ever written, which is the only
place a rule like this can be both simple and true. The template may
then insert its span, because nothing in the value can be markup.

Enforced twice, deliberately and at different moments: the studio panel
refuses a value as it is typed, and the launch gate refuses a file that
somebody edited by hand. Neither is a substitute for the other — the
first is how a person finds out, the second is what the build cannot
get past.

Measured before the rule was written: 1043 string values across the
content, the French page and the configuration, and not one of them
contains `<` or `>`. Refusing them costs nothing that is being used.
"""
from __future__ import annotations

OPEN = "(("
CLOSE = "))"


def trouble(value: str, what: str = "that text") -> "str | None":
    """What is wrong with this value, or None if nothing is.

    The message is the point: it goes to a person who is writing a
    sentence, not to a programmer reading a stack trace.
    """
    for bad in ("<", ">"):
        if bad in value:
            return (
                f"{what} contains {bad!r}. Angle brackets cannot be written "
                f"into the page: a headline may carry two typefaces, and the "
                f"only way to mark that is {OPEN}like this{CLOSE} — so the "
                f"page refuses anything else that looks like markup"
            )

    # Balanced, in order, and never one inside another. A `((` with no
    # `))` would leave a span hanging open and take the rest of the page
    # into the second face.
    depth = 0
    i = 0
    while i < len(value):
        if value.startswith(OPEN, i):
            if depth:
                return (
                    f"{what} opens {OPEN} inside another {OPEN}. One stretch "
                    f"at a time: the page has two typefaces, not a tree of "
                    f"them"
                )
            depth += 1
            i += 2
            continue
        if value.startswith(CLOSE, i):
            if not depth:
                return (
                    f"{what} closes {CLOSE} without opening {OPEN} first, so "
                    f"the page would be left with a stray bracket where a "
                    f"typeface was meant to change"
                )
            depth -= 1
            i += 2
            continue
        i += 1

    if depth:
        return (
            f"{what} opens {OPEN} and never closes it. Everything after it "
            f"would be set in the second typeface, to the end of the page"
        )
    return None


def marked(value: str) -> int:
    """How many stretches of this value are in the second face."""
    return 0 if trouble(value) else value.count(OPEN)
