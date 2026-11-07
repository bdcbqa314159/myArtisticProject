#!/usr/bin/env python3
"""The DeepL drafting path, exercised without DeepL.

    python3 tools/translate-check.py

A stand-in server speaking DeepL's wire format, pointed at by
`DEEPL_API_URL`. Everything between "a field needs translating" and "the
French page has a draft in it and the ledger knows" runs for real: the
request shape, the authorisation header, the batching, the writing into
scalars and into list entries, the ledger, and what happens when the
answer is a refusal.

What is NOT tested here is DeepL — whether the French it returns is any
good, and whether the key works. Neither is testable without a key, and
the first is not testable at all: it is a judgement, made by someone who
reads French.

The real files are never touched. Every case runs against a temporary
pair of pages with the module's paths pointed at them.
"""

import contextlib
import http.server
import importlib.util
import io
import json
import os
import socketserver
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("tr", ROOT / "tools" / "translate.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

SEEN: "list[dict]" = []
REPLY = {"code": 200}


class Stand_in(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(body, keep_blank_values=True)
        SEEN.append({
            "auth": self.headers.get("Authorization", ""),
            "texts": form.get("text", []),
            "target": (form.get("target_lang") or [""])[0],
            "source": (form.get("source_lang") or [""])[0],
            "formality": (form.get("formality") or [""])[0],
            "preserve": (form.get("preserve_formatting") or [""])[0],
        })

        code = REPLY["code"]
        if code != 200:
            self.send_error(code)
            return

        count = len(form.get("text", []))
        if REPLY.get("short"):
            count = max(0, count - 1)
        out = json.dumps({"translations": [
            {"text": f"[fr] {t}"} for t in form.get("text", [])[:count]
        ]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a) -> None:
        pass


EN_PAGE = '''+++
title = "10MILES"
template = "index.html"

[extra]
eyebrow = "Artist-led creative direction"
intro = "A sentence with \\u00ab quotes \\u00bb in it."
video = ""
ecosystem_title = ["Independent by design.", "Collaborative by nature."]
nav = [
  { label = "Approach", href = "#approach" },
  { label = "Contact",  href = "#contact" },
]

[[extra.work]]
name = "Reference 01"
image = "fragment-01.jpg"
+++
'''


def fresh(tmp: Path) -> None:
    (tmp / "content").mkdir(exist_ok=True)
    # Both modules report paths relative to their own root, so the root
    # moves with the files rather than the messages crashing on them.
    tr.ROOT = tmp
    tr.fr.ROOT = tmp
    en = tmp / "content" / "_index.md"
    en.write_text(EN_PAGE, encoding="utf-8")
    tr.fr.EN = en
    tr.fr.FR = tmp / "content" / "_index.fr.md"
    tr.fr.LEDGER = tmp / "content" / "_index.fr.drafts.txt"
    if tr.fr.FR.exists():
        tr.fr.FR.unlink()
    if tr.fr.LEDGER.exists():
        tr.fr.LEDGER.unlink()
    tr.fr.scaffold()
    SEEN.clear()
    REPLY["code"] = 200
    REPLY.pop("short", None)


def main() -> int:
    server = socketserver.TCPServer(("127.0.0.1", 0), Stand_in)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    os.environ["DEEPL_API_URL"] = f"http://127.0.0.1:{port}/v2/translate"
    os.environ["DEEPL_API_KEY"] = "test-key:fx"

    failures: "list[str]" = []

    def ok(condition: bool, what: str) -> None:
        if not condition:
            failures.append(what)

    # The tools under test report what they are doing, which is right
    # when a person runs them and noise when a test does.
    quiet = contextlib.redirect_stdout(io.StringIO())

    with tempfile.TemporaryDirectory() as raw, quiet:
        tmp = Path(raw)

        # --- a plain run -------------------------------------------------
        fresh(tmp)
        tr.draft([], "default")
        page = tr.fr.fields(tr.fr.front_matter(tr.fr.FR))
        ledger = tr.fr.ledger_keys()

        ok(page["eyebrow"][1] == "[fr] Artist-led creative direction",
           "a scalar field is written back")
        ok(page["ecosystem_title[0]"][1] == "[fr] Independent by design.",
           "a list entry is written back")
        ok(page["nav[0].label"][1] == "[fr] Approach",
           "an inline-table label is written back")
        ok("eyebrow" in ledger and "nav[0].label" in ledger,
           "every drafted field lands in the ledger")

        # --- what must never go over the wire ----------------------------
        sent = [t for call in SEEN for t in call["texts"]]
        ok("10MILES" not in sent, "the brand is never sent")
        ok("fragment-01.jpg" not in sent, "a filename is never sent")
        ok("#approach" not in sent, "a fragment link is never sent")
        ok(page["nav[0].href"][1] == "#approach", "and the link is untouched")
        ok(page["title"][1] == "10MILES", "and the brand is untouched")

        # --- the request itself ------------------------------------------
        ok(SEEN[0]["auth"] == "DeepL-Auth-Key test-key:fx",
           "the key goes in the Authorization header")
        ok(SEEN[0]["target"] == "FR" and SEEN[0]["source"] == "EN",
           "the languages are stated")
        ok(SEEN[0]["preserve"] == "1",
           "formatting is preserved, so the typography survives")
        ok(SEEN[0]["formality"] == "",
           "formality is omitted unless asked for")

        # --- the brand filter, tested on its own -------------------------
        #
        # Normally two things keep the trademark off the wire: the
        # scaffold copies it rather than placeholdering it, AND draft()
        # filters it. Mutation testing showed the second could be deleted
        # without any assertion noticing, because the first still held.
        # A guard nothing tests is a guard that leaves one day.
        #
        # So: put the placeholder on the brand and on a filename by hand,
        # as a careless edit would, and require them still not to be sent.
        fresh(tmp)
        hand = tr.fr.FR.read_text(encoding="utf-8")
        hand = hand.replace('title = "10MILES"', f'title = "{tr.fr.PLACEHOLDER}"')
        hand = hand.replace('image = "fragment-01.jpg"',
                            f'image = "{tr.fr.PLACEHOLDER}"')
        tr.fr.FR.write_text(hand, encoding="utf-8")
        tr.draft([], "default")
        after = tr.fr.fields(tr.fr.front_matter(tr.fr.FR))
        sent_now = [t for call in SEEN for t in call["texts"]]
        ok("10MILES" not in sent_now and tr.fr.PLACEHOLDER not in sent_now,
           "a hand-placeholdered brand is still never sent")
        ok(after["title"][1] == tr.fr.PLACEHOLDER,
           "and it is left alone rather than filled in")
        ok(after["extra.work[0].image"][1] == tr.fr.PLACEHOLDER,
           "same for a filename")

        # --- formality is passed through, not chosen ---------------------
        fresh(tmp)
        tr.draft([], "prefer_less")
        ok(SEEN[0]["formality"] == "prefer_less", "formality reaches DeepL")

        # --- a second run has nothing left to do -------------------------
        fresh(tmp)
        tr.draft([], "default")
        calls = len(SEEN)
        tr.draft([], "default")
        ok(len(SEEN) == calls,
           "a second run sends nothing — drafts are not re-fetched")

        # --- a fully drafted page is still a draft -----------------------
        #
        # The hole this closes: the scaffold decides `draft = true` from
        # how many placeholders are left. Draft every field by machine
        # and there are none — the flag comes off, and a page nobody has
        # read is ready to publish. The drafter would have defeated the
        # gate by doing its job.
        fresh(tmp)
        tr.draft([], "default")
        tr.fr.scaffold()
        after_all = tr.fr.FR.read_text(encoding="utf-8")
        page_now = tr.fr.fields(tr.fr.front_matter(tr.fr.FR))
        ok(tr.fr.PLACEHOLDER not in [v for _n, v in page_now.values()],
           "every field really was drafted")
        ok("draft = true" in after_all,
           "a page that is all machine draft is still held back")
        ok(tr.fr.ledger_keys(), "and the ledger still names them")

        # ...and once they are all reviewed, it is not.
        tr.reviewed(tr.fr.ledger_keys())
        tr.fr.scaffold()
        ok("draft = true" not in tr.fr.FR.read_text(encoding="utf-8"),
           "once reviewed, the page is released")

        # --- marking one reviewed ----------------------------------------
        # Its own state, deliberately: this used to inherit a ledger from
        # the block above, so inserting a case between them broke it.
        fresh(tmp)
        tr.draft([], "default")
        before = len(tr.fr.ledger_keys())
        tr.reviewed(["eyebrow"])
        ok(len(tr.fr.ledger_keys()) == before - 1, "a reviewed key leaves the ledger")
        ok("eyebrow" not in tr.fr.ledger_keys(), "and it is the right one")

        # --- refusals are reported, and nothing is written ---------------
        for code, what in ((403, "a refused key"), (429, "too many requests"),
                           (456, "an exhausted quota")):
            fresh(tmp)
            REPLY["code"] = code
            tr.draft([], "default")
            page = tr.fr.fields(tr.fr.front_matter(tr.fr.FR))
            ok(page["eyebrow"][1] == tr.fr.PLACEHOLDER,
               f"{what} leaves the page untouched")
            ok(tr.fr.ledger_keys() == [], f"{what} leaves the ledger empty")

        # --- a short answer is refused rather than guessed ---------------
        # Getting back fewer translations than were sent would misalign
        # every value after the gap: field 3's French on field 2's line.
        fresh(tmp)
        REPLY["short"] = True
        tr.draft([], "default")
        page = tr.fr.fields(tr.fr.front_matter(tr.fr.FR))
        ok(page["eyebrow"][1] == tr.fr.PLACEHOLDER,
           "a short answer writes nothing rather than misaligning")

        # --- quotes in a translation cannot break the file ---------------
        fresh(tmp)
        ok(tr.quote_safe('He said "oui"') == 'He said \\"oui\\"',
           "a quote in a translation is escaped")

        # --- no key, no call ----------------------------------------------
        fresh(tmp)
        os.environ["DEEPL_API_KEY"] = ""
        tr.ENV = tmp / "nonexistent.env"
        code = tr.draft([], "default")
        ok(code == 1 and not SEEN, "with no key it explains itself and sends nothing")
        os.environ["DEEPL_API_KEY"] = "test-key:fx"

    server.shutdown()

    if failures:
        print("\n  TRANSLATION\n")
        for f in failures:
            print(f"    - {f}")
        print()
        return 1
    print("\n  translate: the drafting path holds at 29 points "
          "(DeepL itself stubbed)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
