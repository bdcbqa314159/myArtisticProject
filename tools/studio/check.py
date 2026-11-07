#!/usr/bin/env python3
"""What the studio panel must never do.

    python3 tools/studio/check.py

The panel writes to the files the site is built from, and it is the one
tool here with a graphical surface — so the things it must refuse are
exactly the things nobody will think to try by hand.

Every case below is a bug that existed. The control-character one wrote
a file that `objects.check()` approved and `zola build` then refused,
which is the shape of failure that matters most: a panel that can break
the site from a text box is not an editor, it is a hazard.

Runs against a COPY. The real content file is never touched.
"""

import importlib.util
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "studio"))

import contextlib                                           # noqa: E402
import io                                                   # noqa: E402

import edit                                                 # noqa: E402
import objects                                              # noqa: E402

SERVER = (ROOT / "tools" / "studio" / "server.py").read_text(encoding="utf-8")


def main() -> int:
    bad: "list[str]" = []

    def ok(condition: bool, what: str) -> None:
        if not condition:
            bad.append(what)

    def saying(call, fragment: str, what: str) -> None:
        """Refused, AND for the stated reason.

        Several of these guards are doubled: remove the early, friendly
        one and `objects.check()` still refuses inside `_commit`. Good
        for safety and useless for testing — mutation showed the early
        guard could be deleted with every assertion still passing. So
        where the MESSAGE is the thing a person acts on, the message is
        what gets asserted.
        """
        try:
            call()
        except edit.Refused as problem:
            if fragment.lower() not in str(problem).lower():
                bad.append(f"{what} — refused, but said {str(problem)!r}")
            return
        except Exception as problem:                        # noqa: BLE001
            bad.append(f"{what} — raised {problem!r} instead of refusing")
            return
        bad.append(what)

    def refuses(call, what: str) -> None:
        try:
            call()
        except edit.Refused:
            return
        except Exception as problem:                        # noqa: BLE001
            bad.append(f"{what} — raised {problem!r} instead of refusing")
            return
        bad.append(what)

    # The writers report what they did, which is right for a person and
    # noise for a test.
    with tempfile.TemporaryDirectory() as raw, contextlib.redirect_stdout(io.StringIO()):
        tmp = Path(raw)
        shutil.copytree(ROOT / "content", tmp / "content")
        # ROOT as well as CONTENT. `attach` writes the photograph to
        # `ROOT/content/<name>`, so patching only the front-matter path
        # left this check dropping real image files into the repository —
        # found by `git status`, not by the check, which is the wrong way
        # round and the reason it is written down here.
        edit.ROOT = tmp
        edit.CONTENT = tmp / "content" / "_index.md"
        # `_commit` re-checks with objects.check(), which reads its OWN
        # path — so without this the panel's safety net was validating
        # the real file while the test edited a copy, and every refusal
        # it is supposed to make looked like an acceptance.
        objects.CONTENT = edit.CONTENT
        edit.CONFIG = tmp / "config.toml"
        shutil.copy2(ROOT / "config.toml", edit.CONFIG)
        original = edit.CONTENT.read_text(encoding="utf-8")

        # --- the characters that cannot be written ----------------------
        # A TOML basic string is ended by a quote and escaped by a
        # backslash — both handled — and is INVALID if it carries a raw
        # control character. That is the whole set, which is why input
        # validation is enough here and no build is needed to prove it.
        for code in (0x00, 0x07, 0x0b, 0x0c, 0x1f, 0x7f):
            refuses(lambda c=code: edit.set_text("about_title", f"a{chr(c)}b"),
                    f"a control character ({code}) was accepted into the page")
        for code in (0x0a, 0x0d):
            refuses(lambda c=code: edit.set_text("about_title", f"a{chr(c)}b"),
                    f"a newline ({code}) was accepted into the page")

        # EVERY writer, not just the one. There are three ways into these
        # files — a page sentence, an object field, a config value — and
        # mutation testing found this: deleting the guard from `write`
        # changed nothing here, because only `set_text` was being tried.
        # A check that covers one of three doors is a check that will be
        # believed about all three.
        refuses(lambda: edit.write("reference", 1, "name", "a\x07b"),
                "a control character was accepted into an object field")
        refuses(lambda: edit.set_config("extra.contact", "vcard_role", "a\x07b"),
                "a control character was accepted into the configuration")
        refuses(lambda: edit.attach("reference", 1, "x.jpg", b"\xff\xd8\xff" + b"0" * 20000,
                                    "a\x07b"),
                "a control character was accepted as a photograph's description")

        # ...and the ordinary ones still are. A refusal that is too broad
        # is its own bug: this is a French site, and the client's own
        # words carry accents, apostrophes and dashes.
        for text in ("Créer, c'est décider", "Déjà — vu", 'He said "oui"',
                     "a\\b", "Ænigma · 100 %"):
            try:
                edit.set_text("about_title", text)
            except edit.Refused as problem:
                bad.append(f"ordinary text was refused: {text!r} ({problem})")

        # ...and what was written survives the round trip intact.
        edit.set_text("about_title", 'He said "oui" — déjà')
        line = re.search(r'^about_title = (.*)$',
                         edit.CONTENT.read_text(encoding="utf-8"), re.M)
        ok(line is not None and line.group(1) == r'"He said \"oui\" — déjà"',
           "a quote in a value was not escaped on the way into the file")

        # --- the allowlist ----------------------------------------------
        # The [extra] block also holds the film, the poster and the
        # navigation. A panel that could reach those could point the page
        # at a film that is not there, or empty the menu.
        for key in ("video", "poster", "nav", "ecosystem_fields",
                    "ecosystem_title", "title", "template"):
            refuses(lambda k=key: edit.set_text(k, "x"),
                    f"{key} is writable from the panel and must not be")

        refuses(lambda: edit.set_text("about_title", ""),
                "an empty value was accepted")
        refuses(lambda: edit.set_text("about_title", "x" * (edit.MAX_LEN + 1)),
                "an over-long value was accepted")

        # --- only above the first object --------------------------------
        # `name` and `text` appear inside every reference too. Writing a
        # heading into a reference would be a quiet disaster to find.
        before = edit.CONTENT.read_text(encoding="utf-8")
        cut = before.index("\n[[")
        edit.set_text("work_note", "Changed by the check.")
        after = edit.CONTENT.read_text(encoding="utf-8")
        ok(after[after.index("\n[["):] == before[cut:],
           "writing a page field changed something inside the objects")

        # --- the record is not editable ---------------------------------
        # A verified role is verified by checking it against something.
        # A box a browser could tick would make the gate meaningless.
        for field in ("verified", "verified_on", "evidence", "image"):
            refuses(lambda f=field: edit.write("reference", 1, f, "x"),
                    f"{field} is writable from the panel and must not be")

        # --- a bad edit is undone, not reported ------------------------
        edit.CONTENT.write_text(original, encoding="utf-8")
        refuses(lambda: edit.write("reference", 1, "name", ""),
                "an empty required field was accepted")
        ok(edit.CONTENT.read_text(encoding="utf-8") == original,
           "a refused edit left the file changed")

        # --- photographs -------------------------------------------------
        # The panel can now drop a file onto the page, which makes these
        # the checks standing between a portfolio and a broken image.
        jpeg = b"\xff\xd8\xff" + b"0" * 30000
        png = bytes.fromhex("89504e470d0a1a0a") + b"0" * 30000

        saying(lambda: edit.attach("reference", 1, "x.jpg", jpeg, ""),
               "description",
               "a photograph with no description is refused, but not for a "
               "reason anyone can act on")
        refuses(lambda: edit.attach("reference", 1, "x.jpg", b"not an image" * 3000,
                                    "a description"),
                "a file that is not an image was accepted")
        refuses(lambda: edit.attach("reference", 1, "x.jpg", b"", "a description"),
                "an empty file was accepted")
        refuses(lambda: edit.attach("reference", 1, "x.jpg",
                                    b"\xff\xd8\xff" + b"0" * (edit.MAX_IMAGE + 1),
                                    "a description"),
                "a photograph past the size limit was accepted")
        saying(lambda: edit.attach("capability", 1, "x.jpg", jpeg, "a description"),
               "photograph",
               "attaching a photograph to something that has none is refused, "
               "but not for a reason anyone can act on")
        refuses(lambda: edit.attach("reference", 1, "x.jpg", jpeg, edit.UNWRITTEN),
                "the placeholder was accepted as a description")

        # The extension comes from the CONTENT. A PNG called .jpg is a
        # thing people really do send, and a name that lies about what a
        # file is misleads every tool that touches it afterwards.
        edit.attach("reference", 1, "misnamed.jpg", png, "A PNG, misnamed.")
        named = re.search(r'^image = "(.*)"$',
                          edit.CONTENT.read_text(encoding="utf-8"), re.M)
        ok(named is not None and named.group(1).endswith(".png"),
           "a PNG sent as .jpg was stored under the name it lied about")

        # Never overwrite: another object may point at the file that is
        # already there, and replacing it would change that one silently.
        edit.attach("reference", 2, "misnamed.png", png[:-1] + b"1", "A different one.")
        both = re.findall(r'^image = "(.*)"$',
                          edit.CONTENT.read_text(encoding="utf-8"), re.M)
        ok(len(set(both)) == len(both),
           "two references ended up pointing at the same photograph")

        # --- projects and their photographs ------------------------------
        edit.CONTENT.write_text(original, encoding="utf-8")
        edit.add_project(1)
        edit.add_project(1)
        made = objects.blocks(objects.front_matter(), "extra.project")
        ok([p["id"] for p in made] == ["r1-a", "r1-b"],
           f"a second project did not get its own id: {[p['id'] for p in made]}")

        # `saying`, not `refuses`: the checker refuses these too, so
        # deleting the early guard left every assertion passing and the
        # message useless. Third time this pattern has appeared — the
        # guard that is doubled is the guard that needs its words tested.
        saying(lambda: edit.add_project(0), "no reference 0",
               "a project on reference 0 is refused, but not for a reason "
               "anyone can act on")
        saying(lambda: edit.add_project(99), "no reference 99",
               "a project on reference 99 is refused, but not for a reason "
               "anyone can act on")

        edit.attach_photo("r1-a", "une.jpg", jpeg, "Une description.")
        edit.attach_photo("r1-a", "deux.jpg", jpeg + b"x", "Une autre.")
        shots = objects.blocks(objects.front_matter(), "extra.photo")
        ok(len(shots) == 2, f"a reel did not grow: {len(shots)} photographs")
        ok(len({s["file"] for s in shots}) == 2,
           "two photographs ended up as the same file")

        saying(lambda: edit.attach_photo("r1-a", "x.jpg", jpeg, ""),
               "description",
               "a photograph into a reel with no description is refused, but "
               "not for a reason anyone can act on")
        saying(lambda: edit.attach_photo("ghost", "x.jpg", jpeg, "Une description."),
               "no project has the id",
               "a photograph into a project that does not exist is refused, "
               "but not for a reason anyone can act on")
        refuses(lambda: edit.attach_photo("r1-a", "x.jpg", b"nope" * 3000, "Une description."),
                "a file that is not an image was added to a reel")

        # BOTH OR NEITHER. Removing a project alone leaves its
        # photographs naming something gone — which the checker refuses,
        # so the edit is undone and the button looks broken rather than
        # forbidden.
        edit.remove_project("r1-a")
        after = objects.front_matter()
        ok(not any(p["id"] == "r1-a" for p in objects.blocks(after, "extra.project")),
           "the project was not removed")
        ok(not objects.blocks(after, "extra.photo"),
           "a removed project left its photographs behind, naming nothing")
        refuses(lambda: edit.remove_project("ghost"),
                "removing a project that does not exist was accepted")

        edit.CONTENT.write_text(original, encoding="utf-8")
        refuses(lambda: edit.write("reference", 99, "name", "x"),
                "an index past the end was accepted")
        refuses(lambda: edit.write("nonesuch", 1, "name", "x"),
                "an unknown object kind was accepted")

    # --- the panel's own page ------------------------------------------
    # Structural, because the browser half cannot be driven here: the
    # headless browser runs no animation frames and cannot click. These
    # guard the two fixes most likely to be undone by someone tidying.
    ok('doc.addEventListener("click"' in SERVER and "}, true);" in SERVER,
       "the frame's clicks are no longer caught in the capture phase — "
       "bound to elements instead, the site's own handlers run first and "
       "clicking a button to rename it scrolls the page")
    ok("new AbortController()" in SERVER,
       "an edit no longer cleans up its listeners, so a second edit of the "
       "same element saves twice")
    ok("innerText" in SERVER and ".innerHTML" not in SERVER,
       "the panel reads innerHTML somewhere — pasted markup would reach a "
       "line of TOML")
    ok("data-reel" in SERVER and '"/photo"' in SERVER,
       "a photograph can no longer be dropped onto a project's reel")
    ok('"/project-add"' in SERVER and '"/project-remove"' in SERVER,
       "the panel can no longer add or remove a project")
    ok("data-photo" in SERVER and 'ev.dataTransfer' in SERVER,
       "the panel no longer accepts a photograph dropped on the page")
    ok(SERVER.count('doc.addEventListener("dragover"') >= 1
       and SERVER.count('doc.addEventListener("drop"') >= 1,
       "a file dropped OUTSIDE a photograph is no longer swallowed — the "
       "browser's default navigates the frame away to the bare file, and "
       "there is no obvious way back")
    ok("cache: \"no-store\"" in SERVER,
       "the rebuild poll can be served from cache, which would make it "
       "see the old page for ever")

    # --- the guide quotes the panel, so the panel must still say it ----
    #
    # GUIDE.fr.md walks a non-technical reader through the panel in
    # French, quoting its English wording at each step. The moment a
    # message is reworded the guide describes something that is not on
    # screen — which is the usual way a handover document turns into a
    # lie, and the reason OBJECTS.md is generated rather than written.
    guide = ROOT / "GUIDE.fr.md"
    if guide.exists():
        quoted = set(re.findall(r"«\s*(.*?)\s*»", guide.read_text(encoding="utf-8")))
        for phrase in sorted(quoted):
            # Typographic quotes are the guide's; the source uses plain
            # ones, and the ellipsis survives either way.
            if phrase.replace("\u2019", "'") not in SERVER:
                bad.append(
                    f"GUIDE.fr.md quotes the panel saying {phrase!r}, and it "
                    "does not say that any more"
                )

    if bad:
        print("\n  THE STUDIO PANEL\n")
        for b in bad:
            print(f"    - {b}")
        print()
        return 1

    print("\n  studio: the panel refuses what it must, at 56 points, and the guide still quotes it correctly\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
