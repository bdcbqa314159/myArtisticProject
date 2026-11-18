#!/usr/bin/env python3
"""The studio panel — the site's content, without a text editor.

    python3 tools/studio/server.py [port] [preview-url]

Started by ./preview.sh beside `zola serve`. Standard library only: no
build, no binary, nothing to install. The same arrangement myBureau uses,
for the same reason — the person this is for should double-click one
thing.

SLICE 1 READS AND WRITES NOTHING. It shows what is in content/_index.md,
grouped by object class, with the required fields marked and the missing
ones named. That is the whole architecture with none of the risk, and it
is already useful: it is the first time the content can be seen without
opening TOML.

The schema comes from tools/objects.py, which is also what validates and
what generates OBJECTS.md. One definition, three consumers.
"""

import base64
import html
import urllib.error
import urllib.parse
import urllib.request
import re
import subprocess
import http.server
import json
import secrets
import traceback
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from objects import LOCKED, SCHEMA, blocks, front_matter  # noqa: E402
from edit import (CONFIG, CONFIG_FIELDS, CONTENT, MAX_IMAGE, TEXT_FIELDS,  # noqa: E402
                  Refused, add, remove_font, remove_logo, set_font, set_logo,
                  add_project, attach, attach_dossier, attach_photo,
                  attach_showreel, remove, remove_dossier, remove_photo,
                  remove_showreel,
                  remove_project, set_config, set_text, write)

# A token in the path, as myBureau does. The panel binds to loopback, so
# this is not about the network — it is about the other pages open in the
# same browser, which cannot read this URL and so cannot reach the panel.
TOKEN = secrets.token_urlsafe(16)

# Where `zola serve` is. preview.sh knows, because it chose the port, and
# tells us — guessing 1111 is how "see the site" opens a dead tab on the
# second run of the day.
SITE = {"url": ""}


HERE = Path(__file__).resolve().parent


def document(name: str) -> str:
    """One of the panel's two pages, from the file beside this one.

    They were triple-quoted strings here — 788 of this file's 1415
    lines, and neither of them Python. `panel.html` is the framed site
    with its editing, `list.html` is everything as a list.

    Read on every request rather than cached: the panel is a local tool
    someone is editing while it runs, and a reload showing the file as
    it now is beats a restart nobody knew was needed.
    """
    page = HERE / name
    if not page.exists():
        raise SystemExit(f"\n  the panel is missing {name}. It lives beside "
                         f"tools/studio/server.py\n")
    return page.read_text(encoding="utf-8")


def field_row(value: str, required: bool, what: str, name: str,
              kind: str = "", index: int = 0) -> str:
    missing = required and not value.strip()
    locked = name in LOCKED

    if locked:
        shown = html.escape(value) if value.strip() else "<em>not set</em>"
        cell = f'<span class="locked" title="not editable here">{shown}</span>'
    else:
        cell = (
            f'<input value="{html.escape(value, quote=True)}" '
            f'data-kind="{kind}" data-index="{index}" data-field="{name}" '
            f'aria-label="{html.escape(name)}">'
        )

    return f"""
    <tr class="{'missing' if missing else ''}">
      <th>{html.escape(name)}{'<i>required</i>' if required else ''}</th>
      <td>{cell}</td>
      <td class="what">{html.escape(what)}</td>
    </tr>"""


def config_value(section: str, key: str) -> str:
    text = CONFIG.read_text(encoding="utf-8")
    header = re.search(rf"^\[{re.escape(section)}\]\s*$", text, re.M)
    if not header:
        return ""
    rest = text[header.end():]
    nxt = re.search(r"^\[", rest, re.M)
    block = rest[: nxt.start()] if nxt else rest
    found = re.search(rf'^{re.escape(key)}\s*=\s*"([^"]*)"', block, re.M)
    return found.group(1) if found else ""


def text_values() -> "dict[str, str]":
    """What each of the page's own sentences currently says.

    The scalars only — everything before the first `[[array]]`, which
    is the same cut `set_text` makes. Without it `name = "..."` inside
    a reference would be read as a page-level field.
    """
    body = CONTENT.read_text(encoding="utf-8")
    front = body.split("+++")[1] if body.count("+++") >= 2 else body
    cut = front.find("\n[[")
    return {
        m.group(1): m.group(2)
        for m in re.finditer(r'^([a-z_]+)\s*=\s*"((?:[^"\\]|\\.)*)"',
                             front if cut < 0 else front[:cut], re.M)
    }


def faces_section() -> str:
    """The typeface they chose, and whether a visitor will actually see it.

    The two halves are shown together on purpose. A stack naming a face
    with no file loaded is the state this whole section exists to make
    visible: the panel used to accept `Canela, Georgia, serif` and say
    nothing, and every visitor read Georgia.
    """
    import fonts

    have = fonts.installed()
    rows = []
    for slot, (name, which, weight, what) in fonts.SLOTS.items():
        here = slot in have
        try:
            named = fonts.family(which)
            trouble = ""
        except fonts.Rejected as no:
            named, trouble = "", str(no)

        if trouble:
            state = trouble
        elif here:
            state = f"loaded as {named!r} at {weight}"
        else:
            after = ", ".join(p.strip() for p in
                              fonts.stack(which).split(",")[1:])
            state = (f"{named!r} is named but no file is in place — a visitor "
                     f"sees {after or 'whatever they have'}")
        off = (f'<button class="unface" data-slot="{slot}">remove</button>'
               if here else "")
        rows.append(f"""
        <tr class="{'' if here else 'missing'}">
          <th>{html.escape(name)}</th>
          <td><input type="file" accept=".woff2,font/woff2" data-face="{slot}"
                     aria-label="{html.escape(name)}">{off}</td>
          <td class="what">{html.escape(what)} — {html.escape(state)}</td>
        </tr>""")

    return (
        f'<section><h2>the typeface<span class="count">{len(have)} of '
        f'{len(fonts.SLOTS)}</span></h2>'
        '<p class="doc">Two halves, and neither works alone: the name goes in '
        'launch below (theme.serif and theme.sans), and the file goes here. '
        'Naming a face nobody has installed changes nothing by itself — the '
        'browser quietly draws the next one in the stack, which is what it '
        'did before this section existed. woff2 only.</p>'
        f'<table>{"".join(rows)}</table></section>'
    )


def marks_section() -> str:
    """Their own logo, in the three places a browser asks for one.

    Three slots rather than one, and nothing converted between them:
    there is no rasteriser here, so an SVG cannot become the two PNGs.
    The alternative would be a dependency, or guessing a crop of
    someone's mark — and the three files are what a handover gives you
    anyway. `tools/logo.py` says what each one must be.
    """
    import logo

    have = logo.installed()
    rows = []
    for slot, (name, _judge, what) in logo.SLOTS.items():
        here = slot in have
        state = (f"{len(have[slot]) // 1024 or 1}KB in place" if here
                 else "the drawn mark stands")
        off = (f'<button class="unmark" data-slot="{slot}">remove</button>'
               if here else "")
        accept = "image/svg+xml" if slot == "logo" else "image/png"
        rows.append(f"""
        <tr class="{'' if here else 'missing'}">
          <th>{html.escape(name)}</th>
          <td><input type="file" accept="{accept}" data-slot="{slot}"
                     aria-label="{html.escape(name)}">{off}</td>
          <td class="what">{html.escape(what)} — {html.escape(state)}</td>
        </tr>""")

    return (
        f'<section><h2>the mark<span class="count">{len(have)} of '
        f'{len(logo.SLOTS)}</span></h2>'
        '<p class="doc">Until the logo exists, the tab carries a mark drawn by '
        'the studio — a point on a circle, no letterform. Drop the real one '
        'here and it replaces that everywhere: the tab, the icon iOS puts on '
        'a home screen, and the picture under a pasted link. An SVG for the '
        'tab, a square PNG for the icon, and 1200x630 for the link. Nothing '
        'is converted between them, so whatever is not dropped keeps the '
        'drawn mark.</p>'
        f'<table>{"".join(rows)}</table></section>'
    )


def words_section() -> str:
    """Every sentence the page says, as a list.

    Clicking a word on the page is the better way to change it and
    stays the first way. It only reaches what is ON the page, though:
    the thirteen replies the form speaks while a message is sent are
    never rendered as text — they sit inside its `data-says` JSON and
    are put on screen by the script — so until this list existed there
    was no way to reword a single one of them.
    """
    now = text_values()
    rows = "".join(
        f"""
        <tr class="{'missing' if not now.get(key, '') else ''}">
          <th>{html.escape(key)}</th>
          <td><input value="{html.escape(now.get(key, ''), quote=True)}"
                     data-text="{key}" aria-label="{html.escape(key)}"></td>
          <td class="what">{html.escape(what)}</td>
        </tr>"""
        for key, what in TEXT_FIELDS.items()
    )
    return (
        f'<section><h2>words<span class="count">{len(TEXT_FIELDS)}</span></h2>'
        '<p class="doc">The page\'s own sentences. Clicking one on the page is '
        'quicker and is still the way to do it — this list is for the ones '
        'with nothing to click: what the message box replies while it sends.</p>'
        f'<table>{rows}</table></section>'
    )


def launch_section() -> str:
    """The fields a launch needs, and what is still missing.

    The gate is shown but not operated: `live` is not editable here.
    Whether the site MAY be published is a question the checks answer;
    whether it IS is a decision a person makes with the repository in
    front of them, not a button in a browser.
    """
    groups = []
    for section, fields in CONFIG_FIELDS.items():
        rows = "".join(
            f"""
            <tr class="{'missing' if not config_value(section, key) else ''}">
              <th>{html.escape(key)}</th>
              <td><input value="{html.escape(config_value(section, key), quote=True)}"
                         data-section="{section}" data-key="{key}"
                         aria-label="{html.escape(key)}"></td>
              <td class="what">{html.escape(what)}</td>
            </tr>"""
            for key, what in fields.items()
        )
        groups.append(
            f'<article><h3>{html.escape(section)}</h3><table>{rows}</table></article>'
        )

    gate = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "content-check.py")],
        capture_output=True, text=True,
    ).stdout
    blocking = [l.strip()[2:] for l in gate.splitlines() if l.strip().startswith("- ")]
    listed = "".join(f"<li>{html.escape(b)}</li>" for b in blocking)

    standing = (
        f'<p class="doc">Still standing between this and a live site:</p><ul class="gate">{listed}</ul>'
        if blocking else '<p class="doc">Nothing is blocking a launch.</p>'
    )

    return (
        '<section><h2>launch<span class="count">'
        f'{len(blocking)} blocking</span></h2>'
        '<p class="doc">The identity, the contact details and the legal notice. '
        'Filled in at handover; the page shows the stand-in until they are.</p>'
        f'{standing}{"".join(groups)}</section>'
    )


def page() -> str:
    fm = front_matter()
    sections = []

    for kind, (array, doc, fields) in SCHEMA.items():
        found = blocks(fm, array)
        items = []
        for i, obj in enumerate(found, 1):
            rows = "".join(
                field_row(obj.get(f, ""), req, what, f, kind, i)
                for f, (req, what) in fields.items()
            )
            label = obj.get("name") or f"{kind} {i}"
            photo = ""
            if kind == "reference":
                has = obj.get("image", "").strip()
                photo = (
                    f'<div class="photo">'
                    f'<label>{"replace the photograph" if has else "add a photograph"}'
                    f'<input type="file" accept="image/jpeg,image/png,image/webp" '
                    f'data-kind="{kind}" data-index="{i}"></label>'
                    f'<label>what it shows<input class="alt" placeholder="required" '
                    f'data-for="{i}"></label>'
                    f"</div>"
                )

            items.append(
                f'<article><h3><span class="n">{i:02d}</span>{html.escape(label)}'
                f'<button class="remove" data-kind="{kind}" data-index="{i}">remove</button>'
                f"</h3><table>{rows}</table>{photo}</article>"
            )
        sections.append(
            f'<section><h2>{html.escape(kind)}<span class="count">{len(found)}</span></h2>'
            f'<p class="doc">{html.escape(doc)}</p>'
            f'{"".join(items) or "<p><em>none</em></p>"}'
            f'<button class="add" data-kind="{kind}">add a {html.escape(kind)}</button>'
            f"</section>"
        )

    return document("list.html").replace(
        "<!--CONTENT-->",
        "".join(sections) + words_section() + marks_section()
        + faces_section() + launch_section())


def shell() -> str:
    """The panel: the real site, and a way into it.

    What was here before was a form — every field of every object in a
    table, nowhere near the page it belonged to. Correct and unpleasant:
    to change a heading you had to know which of eighty rows was that
    heading.

    This frames the site instead, through the panel's own address so the
    frame is same-origin and can be reached into. Click a sentence on
    the page and edit THAT sentence. The form is still here, a keystroke
    away, because a list is the better tool for adding and removing
    things and for the fields that are not words on a page.
    """
    return document("panel.html")


class Panel(http.server.BaseHTTPRequestHandler):
    def from_this_machine(self) -> bool:
        """The request must be addressed to loopback by name as well as
        by route.

        Binding to 127.0.0.1 stops another machine connecting. It does
        NOT stop a page in this browser resolving its own domain to
        127.0.0.1 and talking to the panel — DNS rebinding — and the
        panel writes files. Checking the Host header costs one line and
        closes it: a rebound request arrives naming the attacker's
        domain, not localhost.
        """
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in {"127.0.0.1", "localhost", "[::1]", "::1"}

    def proxy(self, rest: str) -> None:
        """The real site, served from the panel's own address.

        Not a screenshot and not a second renderer: this IS the page Zola
        built, fetched and handed on. Which matters because it makes the
        frame SAME-ORIGIN, and a same-origin frame is one the panel can
        reach into — so a click on the page itself can become an edit.
        There is one renderer in this project and it stays that way.

        EVERY absolute url is rewritten, not just the links. The page
        carries `default-src 'self'`, and once the document sits on this
        address `self` means THIS address — so a stylesheet still
        pointing at Zola's port would be refused by the site's own
        policy. Rewriting all of it keeps the page whole and its policy
        honest.

        The cost is Zola's live-reload, whose socket no longer finds its
        way home. The panel reloads the frame itself after an edit, which
        is one mechanism instead of two.
        """
        site = SITE["url"].rstrip("/")
        try:
            if not site:
                raise OSError("nobody told the panel where the site is")
            with urllib.request.urlopen(site + rest, timeout=20) as answer:
                kind = answer.headers.get("Content-Type", "application/octet-stream")
                body = answer.read()
        except urllib.error.HTTPError as problem:
            self.send_response(problem.code)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        except Exception:                                   # noqa: BLE001
            # This lands INSIDE the frame, where the reader is looking. A
            # stack trace tells them nothing they can act on; a sentence
            # does. Editing still works meanwhile — only the view is gone.
            page = (
                "<!doctype html><meta charset=utf-8>"
                "<style>body{font:14px/1.6 system-ui;margin:3rem;color:#555}"
                "b{color:#111}</style>"
                "<p><b>The site is not answering.</b></p>"
                "<p>It is being rebuilt, or the window running it was closed. "
                "Carry on editing — everything is saved. The view comes back "
                "by itself.</p>"
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if kind.split(";")[0] in ("text/html", "text/css", "application/javascript",
                                  "text/javascript", "application/json"):
            body = body.decode("utf-8", "replace").replace(site, "/site").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self.from_this_machine():
            self.send_error(404)
            return

        # The framed site carries NO token, and cannot: the frame's src is
        # written in the markup and every link inside the page is a plain
        # href. That is not a hole being opened — `zola serve` is already
        # serving these exact bytes, with no token at all, on the same
        # loopback address. This is a second door to a room that was never
        # locked, not a door to a new room. Everything that reads or
        # writes the content still needs the token.
        if self.path == "/site" or self.path.startswith("/site/"):
            return self.proxy(self.path[len("/site"):] or "/")

        if not self.path.startswith(f"/{TOKEN}"):
            # Not a 403: an unauthorised reader should not learn that the
            # path exists and is merely guarded.
            self.send_error(404)
            return
        wants_form = self.path.rstrip("/").endswith("/form")
        body = (page() if wants_form else shell()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # It reads a file that changes under it; never let a browser
        # show a stale view of someone's own content.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self.from_this_machine():
            self.send_error(404)
            return
        if not self.path.startswith(f"/{TOKEN}"):
            self.send_error(404)
            return
        route = self.path.rsplit("/", 1)[-1]
        if route not in {"edit", "add", "remove", "attach", "config", "text",
                         "logo", "logo-remove", "font", "font-remove",
                         "photo", "project-add", "project-remove", "photo-remove",
                         "dossier", "showreel", "dossier-remove",
                         "showreel-remove"}:
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        # base64 is a third larger than the bytes it carries, and a
        # photograph is allowed to be 12MB.
        # A document is bigger than a photograph, and the dossier tool
        # has its own 40MB ceiling — this only has to let one through to
        # the place that judges it.
        # A film is the largest thing this panel ever carries. The
        # verb has its own 120MB ceiling; this only has to let one
        # through to the place that judges it.
        # A mark is kilobytes of geometry, and `tools/logo.py` holds it
        # to 512KB of SVG or 4MB of PNG. This only has to let one
        # through to the place that judges it — and the 8KB floor
        # below, which is right for a line of TOML, refused a 13KB
        # share image with a message about nothing a person can act on.
        cap = (168 * 1024 * 1024 if route == "showreel"
               else 56 * 1024 * 1024 if route == "dossier"
               else int(MAX_IMAGE * 1.4) if route in ("attach", "photo")
               else 6 * 1024 * 1024 if route in ("logo", "font")
               else 8192)
        if length > cap:
            self.reply({"ok": False, "message": "that is more than this accepts"})
            return

        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            kind = str(body.get("kind", ""))

            if route == "photo":
                message = attach_photo(
                    str(body.get("project", "")),
                    str(body.get("filename", "")),
                    base64.b64decode(str(body.get("data", "")), validate=True),
                    str(body.get("alt", "")),
                )
            elif route == "project-add":
                message = add_project(int(body.get("reference", 0)))
            elif route == "project-remove":
                message = remove_project(str(body.get("project", "")))
            elif route == "photo-remove":
                message = remove_photo(str(body.get("file", "")))
            elif route == "text":
                message = set_text(str(body.get("key", "")),
                                   str(body.get("value", "")))
            elif route == "logo":
                message = set_logo(
                    str(body.get("slot", "")),
                    base64.b64decode(str(body.get("data", "")), validate=True),
                )
            elif route == "font":
                message = set_font(
                    str(body.get("slot", "")),
                    base64.b64decode(str(body.get("data", "")), validate=True),
                )
            elif route == "font-remove":
                message = remove_font(str(body.get("slot", "")))
            elif route == "logo-remove":
                message = remove_logo(str(body.get("slot", "")))
            elif route == "config":
                message = set_config(
                    str(body.get("section", "")),
                    str(body.get("key", "")),
                    str(body.get("value", "")),
                )
            elif route == "dossier-remove":
                message = remove_dossier(int(form.get("concept", "0")))

            elif route == "showreel-remove":
                message = remove_showreel()

            elif route == "showreel":
                message = attach_showreel(
                    form.get("filename", ""),
                    form.get("file", b""),
                )

            elif route == "dossier":
                message = attach_dossier(
                    int(form.get("concept", "0")),
                    form.get("filename", ""),
                    form.get("file", b""),
                    form.get("alt", ""),
                )

            elif route == "attach":
                message = attach(
                    kind,
                    int(body.get("index", 0)),
                    str(body.get("filename", "")),
                    base64.b64decode(str(body.get("data", "")), validate=True),
                    str(body.get("alt", "")),
                )
            elif route == "add":
                message = add(kind)
            elif route == "remove":
                message = remove(kind, int(body.get("index", 0)))
            else:
                message = write(
                    kind,
                    int(body.get("index", 0)),
                    str(body.get("field", "")),
                    str(body.get("value", "")),
                )
            self.reply({"ok": True, "message": message})
        except Refused as refused:
            # Expected: the edit was rejected and the file is untouched.
            self.reply({"ok": False, "message": str(refused)})
        except Exception:                              # noqa: BLE001
            # NOT THE SAME THING AS A REFUSAL, and it used to look
            # identical. `Refused` means the edit was rejected and the
            # file is untouched — a promise every writer here keeps.
            # This branch is anything else: a bug, a missing file, a
            # permission. It carried the exception's own words straight
            # to the browser, so a fault read exactly like "you typed
            # that wrong", and an absolute path could end up on screen
            # or in a screenshot.
            #
            # Said plainly instead, and written in full to the panel's
            # own terminal, which is where someone can use it.
            print(f"\n  the panel hit a fault handling /{route}:",
                  file=sys.stderr)
            traceback.print_exc()
            self.reply({
                "ok": False,
                "message": "Something went wrong in the panel, not in what "
                           "you typed. Nothing was changed, and the details "
                           "are in the terminal the panel is running in.",
            })

    def reply(self, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass            # the preview's output is the client's; keep it quiet


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1212
    SITE["url"] = sys.argv[2] if len(sys.argv) > 2 else ""
    url = f"http://127.0.0.1:{port}/{TOKEN}"
    print(url, flush=True)
    server = http.server.HTTPServer(("127.0.0.1", port), Panel)
    if len(sys.argv) <= 1:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
