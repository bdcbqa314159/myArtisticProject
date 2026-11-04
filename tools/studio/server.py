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
import re
import subprocess
import http.server
import json
import secrets
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from objects import LOCKED, SCHEMA, blocks, front_matter  # noqa: E402
from edit import (CONFIG, CONFIG_FIELDS, MAX_IMAGE, Refused, add, attach,  # noqa: E402
                  remove, set_config, write)

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

    return TEMPLATE.replace("<!--CONTENT-->", "".join(sections) + launch_section())


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
button.add,button.remove{font:inherit;cursor:pointer;background:none;color:var(--muted);border:1px solid var(--line);border-radius:3px}
button.add{margin-top:1.5rem;padding:.5rem 1rem;font-size:.8125rem}
button.remove{margin-left:auto;padding:.15rem .5rem;font-size:.6875rem}
button.add:hover,button.remove:hover{color:var(--ink);border-color:var(--muted)}
button:disabled{opacity:.4;cursor:default}
h3{justify-content:space-between}
.photo{display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:1rem;padding-top:1rem;border-top:1px dotted var(--line)}
.photo label{display:flex;flex-direction:column;gap:.35rem;font-size:.75rem;color:var(--muted)}
.photo input[type=file]{font-size:.8125rem;max-width:22rem}
.photo .alt{min-width:22rem}
ul.gate{margin:0 0 2rem;padding-left:1.1rem;color:var(--warn);font-size:.875rem}
ul.gate li{margin:.2rem 0}
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

  function send(path, body, then){
    fetch(location.pathname + path, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    }).then(function(r){ return r.json(); }).then(then)
      .catch(function(e){ tell(String(e), true); });
  }

  /* A photograph and its description go together or not at all. The
     file input does nothing until the description beside it is filled
     in — the refusal is on the server too, but being told after
     choosing a file is a worse way to learn it. */
  document.addEventListener("change", function(ev){
    var el = ev.target;
    if (el.type !== "file" || !el.files || !el.files[0]) return;
    var alt = document.querySelector('.alt[data-for="' + el.dataset.index + '"]');
    if (!alt || !alt.value.trim()) {
      el.value = "";
      alt.focus();
      return tell("What does the photograph show? Describe it first.", true);
    }
    var file = el.files[0];
    tell("reading " + file.name + "…", false);
    var reader = new FileReader();
    reader.onload = function(){
      send("/attach", {
        kind: el.dataset.kind, index: +el.dataset.index,
        filename: file.name, alt: alt.value,
        data: reader.result.split(",")[1]
      }, function(d){
        if (!d.ok) { el.value = ""; return tell(d.message, true); }
        location.reload();
      });
    };
    reader.readAsDataURL(file);
  });

  document.addEventListener("click", function(ev){
    var el = ev.target;
    if (el.classList.contains("add")) {
      el.disabled = true;
      send("/add", {kind: el.dataset.kind}, function(d){
        if (!d.ok) { el.disabled = false; return tell(d.message, true); }
        /* Reload rather than build the new object in the page. The file
           is the truth; showing anything assembled here would be a
           second opinion about what it now contains. */
        location.reload();
      });
    }
    if (el.classList.contains("remove")) {
      if (!confirm("Remove this? It is written to the file immediately.")) return;
      el.disabled = true;
      send("/remove", {kind: el.dataset.kind, index: +el.dataset.index}, function(d){
        if (!d.ok) { el.disabled = false; return tell(d.message, true); }
        location.reload();
      });
    }
  });

  document.addEventListener("change", function(ev){
    var el = ev.target;
    if (el.tagName !== "INPUT") return;
    var isConfig = !!el.dataset.section;
    if (!el.dataset.field && !isConfig) return;
    var was = el.defaultValue;
    el.disabled = true;
    fetch(location.pathname + (isConfig ? "/config" : "/edit"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(isConfig
        ? {section: el.dataset.section, key: el.dataset.key, value: el.value}
        : {kind: el.dataset.kind, index: +el.dataset.index,
           field: el.dataset.field, value: el.value})
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
        route = self.path.rsplit("/", 1)[-1]
        if route not in {"edit", "add", "remove", "attach", "config"}:
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        # base64 is a third larger than the bytes it carries, and a
        # photograph is allowed to be 12MB.
        cap = int(MAX_IMAGE * 1.4) if route == "attach" else 8192
        if length > cap:
            self.reply({"ok": False, "message": "that is more than this accepts"})
            return

        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            kind = str(body.get("kind", ""))

            if route == "config":
                message = set_config(
                    str(body.get("section", "")),
                    str(body.get("key", "")),
                    str(body.get("value", "")),
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
