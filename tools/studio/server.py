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

import html
import http.server
import json
import secrets
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from objects import LOCKED, SCHEMA, blocks, front_matter  # noqa: E402
from edit import Refused, write  # noqa: E402

# A token in the path, as myBureau does. The panel binds to loopback, so
# this is not about the network — it is about the other pages open in the
# same browser, which cannot read this URL and so cannot reach the panel.
TOKEN = secrets.token_urlsafe(16)


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
            items.append(
                f'<article><h3><span class="n">{i:02d}</span>{html.escape(label)}</h3>'
                f"<table>{rows}</table></article>"
            )
        sections.append(
            f'<section><h2>{html.escape(kind)}<span class="count">{len(found)}</span></h2>'
            f'<p class="doc">{html.escape(doc)}</p>{"".join(items) or "<p><em>none</em></p>"}</section>'
        )

    return TEMPLATE.replace("<!--CONTENT-->", "".join(sections))


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Studio</title>
<style>
:root{color-scheme:light dark;--ink:#14171c;--muted:#5e6672;--line:#d7dbe2;--bg:#f4f5f7;--panel:#e8eaee;--warn:#9a3412}
@media(prefers-color-scheme:dark){:root{--ink:#eef1f5;--muted:#9aa3b0;--line:#272c34;--bg:#101317;--panel:#171b21;--warn:#f0a070}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;padding:2rem clamp(1rem,5vw,4rem) 6rem}
h1{font-size:1rem;letter-spacing:.24em;text-transform:uppercase;font-weight:500;color:var(--muted);margin:0 0 2.5rem}
h2{font-size:1.5rem;font-weight:400;margin:3.5rem 0 .25rem;display:flex;align-items:baseline;gap:.75rem}
.count{font-size:.6875rem;letter-spacing:.2em;color:var(--muted)}
.doc{color:var(--muted);font-size:.875rem;max-width:62ch;margin:0 0 1.5rem}
article{border-top:1px solid var(--line);padding:1.25rem 0}
h3{font-size:1rem;font-weight:500;margin:0 0 .75rem;display:flex;gap:.75rem;align-items:baseline}
.n{font-size:.6875rem;letter-spacing:.2em;color:var(--muted)}
table{border-collapse:collapse;width:100%;max-width:70rem}
th{text-align:left;font-weight:400;color:var(--muted);width:10rem;vertical-align:top;padding:.3rem 1rem .3rem 0;font-size:.8125rem}
th i{font-style:normal;color:var(--muted);opacity:.6;font-size:.625rem;letter-spacing:.14em;text-transform:uppercase;display:block}
td{vertical-align:top;padding:.3rem 1rem .3rem 0}
.what{color:var(--muted);font-size:.8125rem;max-width:34ch}
em{opacity:.5;font-style:normal}
tr.missing td em{color:var(--warn);opacity:1;font-weight:500}
footer{margin-top:4rem;color:var(--muted);font-size:.8125rem;border-top:1px solid var(--line);padding-top:1rem}
input{font:inherit;width:100%;max-width:34rem;padding:.3rem .5rem;border:1px solid var(--line);border-radius:3px;background:var(--panel);color:var(--ink)}
input:focus{outline:2px solid var(--muted);outline-offset:1px}
input:disabled{opacity:.5}
.locked{color:var(--muted);border-bottom:1px dotted var(--muted);cursor:help}
.says{position:fixed;left:1rem;bottom:1rem;margin:0;padding:.6rem 1rem;border-radius:3px;font-size:.8125rem;background:var(--panel);color:var(--ink);opacity:0;transition:opacity .2s}
.says.good,.says.bad{opacity:1}
.says.bad{color:var(--warn);font-weight:500}
</style></head><body>
<h1>Studio</h1>
<!--CONTENT-->
<footer>
  Edits are written to <code>content/_index.md</code> and checked before they land.
  Fields shown without a box are deliberately not editable here &mdash; see
  <code>LOCKED</code> in <code>tools/objects.py</code>.
</footer>
<p class="says" role="status" aria-live="polite"></p>
<script>
(function(){
  var says = document.querySelector(".says");
  function tell(text, bad){ says.textContent = text; says.className = "says" + (bad ? " bad" : " good"); }

  document.addEventListener("change", function(ev){
    var el = ev.target;
    if (el.tagName !== "INPUT" || !el.dataset.field) return;
    var was = el.defaultValue;
    el.disabled = true;
    fetch(location.pathname + "/edit", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        kind: el.dataset.kind, index: +el.dataset.index,
        field: el.dataset.field, value: el.value
      })
    })
    .then(function(r){ return r.json(); })
    .then(function(d){
      el.disabled = false;
      if (d.ok) { el.defaultValue = el.value; tell(d.message, false); }
      /* Put the old value back. A field showing something the file does
         not contain is worse than an error message. */
      else { el.value = was; tell(d.message, true); }
    })
    .catch(function(e){ el.disabled = false; el.value = was; tell(String(e), true); });
  });
})();
</script>
</body></html>
"""


class Panel(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not self.path.startswith(f"/{TOKEN}"):
            # Not a 403: an unauthorised reader should not learn that the
            # path exists and is merely guarded.
            self.send_error(404)
            return
        body = page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # It reads a file that changes under it; never let a browser
        # show a stale view of someone's own content.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self.path.startswith(f"/{TOKEN}"):
            self.send_error(404)
            return
        if not self.path.endswith("/edit"):
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length > 8192:
            self.reply({"ok": False, "message": "that is too much for one field"})
            return

        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            message = write(
                str(body.get("kind", "")),
                int(body.get("index", 0)),
                str(body.get("field", "")),
                str(body.get("value", "")),
            )
            self.reply({"ok": True, "message": message})
        except Refused as refused:
            # Expected: the edit was rejected and the file is untouched.
            self.reply({"ok": False, "message": str(refused)})
        except Exception as exc:                       # noqa: BLE001
            self.reply({"ok": False, "message": f"{type(exc).__name__}: {exc}"})

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
