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
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from objects import LOCKED, SCHEMA, blocks, front_matter  # noqa: E402
from edit import (CONFIG, CONFIG_FIELDS, MAX_IMAGE, Refused, add, attach,  # noqa: E402
                  remove, set_config, set_text, write)

# A token in the path, as myBureau does. The panel binds to loopback, so
# this is not about the network — it is about the other pages open in the
# same browser, which cannot read this URL and so cannot reach the panel.
TOKEN = secrets.token_urlsafe(16)

# Where `zola serve` is. preview.sh knows, because it chose the port, and
# tells us — guessing 1111 is how "see the site" opens a dead tab on the
# second run of the day.
SITE = {"url": ""}


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
    return SHELL


SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Studio</title>
<style>
:root{color-scheme:light dark;--ink:#14171c;--muted:#5e6672;--line:#d7dbe2;--bg:#f4f5f7;--accent:#2563eb;--warn:#9a3412}
@media(prefers-color-scheme:dark){:root{--ink:#eef1f5;--muted:#9aa3b0;--line:#272c34;--bg:#101317;--accent:#7aa2f7;--warn:#f0a070}}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;
     display:flex;flex-direction:column}
header{display:flex;align-items:center;gap:1rem;padding:.7rem 1.1rem;border-bottom:1px solid var(--line)}
h1{font-size:.72rem;letter-spacing:.24em;text-transform:uppercase;font-weight:500;color:var(--muted);margin:0}
.grow{flex:1}
a.b,button.b{font:inherit;font-size:.82rem;color:var(--ink);background:none;border:1px solid var(--line);
   border-radius:999px;padding:.3rem .85rem;cursor:pointer;text-decoration:none}
a.b:hover,button.b:hover{border-color:var(--muted)}
#say{font-size:.82rem;color:var(--muted);min-height:1.2em}
#say.bad{color:var(--warn)}
iframe{flex:1;width:100%;border:0;background:var(--bg)}
#sheet{position:fixed;inset:0;background:rgba(0,0,0,.45);display:grid;place-items:center;padding:2rem}
#sheet[hidden]{display:none}
#photo{background:var(--bg);border:1px solid var(--line);border-radius:10px;
  padding:1.4rem;max-width:30rem;width:100%;display:grid;gap:.75rem}
#photo h2{margin:0;font-size:.95rem;font-weight:600}
#pview{max-height:11rem;width:auto;max-width:100%;justify-self:center;border-radius:6px;display:none}
#pview[src]{display:block}
#photo label{font-size:.85rem;display:grid;gap:.2rem}
#photo i{font-style:normal;color:var(--muted);font-size:.78rem}
#photo textarea{font:inherit;font-size:.9rem;padding:.5rem;border:1px solid var(--line);
  border-radius:6px;background:transparent;color:var(--ink);resize:vertical}
#perr{margin:0;min-height:1.1em;font-size:.82rem;color:var(--warn)}
#photo menu{display:flex;gap:.5rem;justify-content:flex-end;margin:0;padding:0}
.b.go{border-color:var(--accent);color:var(--accent)}
</style></head><body>
<header>
  <h1>Studio</h1>
  <span id="say">Click any text on the page to change it.</span>
  <span class="grow"></span>
  <a class="b" id="form" href="">Everything as a list</a>
  <a class="b" id="open" href="/site/" target="_blank">Open the site</a>
</header>
<iframe id="view" src="/site/"></iframe>
<div id="sheet" hidden><form id="photo">
  <h2 id="ptitle">Photograph</h2>
  <img id="pview" alt="">
  <label for="palt">What does it show?<i>Required — it is what someone who cannot see it is read.</i></label>
  <textarea id="palt" rows="3" maxlength="600"></textarea>
  <p id="perr"></p>
  <menu><button type="button" id="pno" class="b">Cancel</button>
        <button id="pyes" class="b go">Save</button></menu>
</form></div>
<script>
const say = (m, bad) => { const s = document.getElementById("say");
  s.textContent = m; s.classList.toggle("bad", !!bad); };
document.getElementById("form").href = location.pathname + "/form";

/* The frame is same-origin — it is the real site, fetched through this
   server — so the page inside it can simply be reached into. No second
   renderer, no copy of the markup here that could disagree with it. */
const view = document.getElementById("view");
let busy = false;

function arm() {
  let doc;
  try { doc = view.contentDocument; } catch (e) { return; }
  if (!doc || !doc.body || doc.getElementById("studio-marks")) return;

  const style = doc.createElement("style");
  style.id = "studio-marks";          /* once per document, not per load */
  style.textContent = `
    [data-edit]{outline:0;transition:background 120ms,box-shadow 120ms;border-radius:3px}
    [data-edit]:hover{background:color-mix(in oklch,currentColor 8%,transparent);
      box-shadow:0 0 0 4px color-mix(in oklch,currentColor 8%,transparent);cursor:text}
    [data-edit][contenteditable="true"]{background:color-mix(in oklch,currentColor 12%,transparent);
      box-shadow:0 0 0 4px color-mix(in oklch,currentColor 12%,transparent)}
    [data-photo]{position:relative;cursor:copy}
    [data-photo]::after{content:attr(data-hint);position:absolute;inset:auto 0 0 0;
      padding:.5rem .7rem;font:500 11px/1.3 system-ui;letter-spacing:.08em;
      text-transform:uppercase;text-align:center;
      background:color-mix(in oklch,currentColor 85%,transparent);
      color:canvas;opacity:0;transition:opacity 140ms;pointer-events:none}
    [data-photo]:hover::after,[data-photo].over::after{opacity:1}
    [data-photo].over{outline:2px dashed currentColor;outline-offset:3px}`;
  doc.head.appendChild(style);

  /* ON THE DOCUMENT, IN THE CAPTURE PHASE.
     Bound to each element instead, this ran AFTER the site's own
     handlers: landing.js binds every `a[href^="#"]` at load, so
     clicking "Explore selected work" to rename it also scrolled the
     frame to Selected Work. Listeners on one element fire in the order
     they were added, and ours is always added second. Capture happens
     before any of them. */
  doc.addEventListener("click", (ev) => {
    const photo = ev.target.closest("[data-photo]");
    if (photo) {
      ev.preventDefault(); ev.stopPropagation();
      if (busy) { say("Still saving the last one.", true); return; }
      return choose(photo);
    }
    const el = ev.target.closest("[data-edit]");
    if (!el || el.isContentEditable) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (busy) { say("Still saving the last one.", true); return; }
    edit(doc, el);
  }, true);

  for (const fig of doc.querySelectorAll("[data-photo]")) {
    fig.dataset.hint = fig.classList.contains("empty")
      ? "Drop a photograph here, or click" : "Drop a new one, or click to replace";
  }

  /* A drop anywhere else in the frame must do NOTHING. Without this the
     browser's default takes over and navigates away from the site to
     the dropped file — the panel's frame replaced by a lone JPEG, and
     no obvious way back. */
  doc.addEventListener("dragover", (ev) => ev.preventDefault());
  doc.addEventListener("drop", (ev) => ev.preventDefault());

  for (const fig of doc.querySelectorAll("[data-photo]")) {
    fig.addEventListener("dragover", (ev) => {
      ev.preventDefault(); ev.stopPropagation(); fig.classList.add("over");
    });
    fig.addEventListener("dragleave", () => fig.classList.remove("over"));
    fig.addEventListener("drop", (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      fig.classList.remove("over");
      if (busy) { say("Still saving the last one.", true); return; }
      const file = ev.dataTransfer && ev.dataTransfer.files[0];
      if (file) ask(fig, file);
    });
  }
}

/* ---- photographs -------------------------------------------------------
 * The file and its description arrive together or not at all — the verb
 * refuses them apart, and so does this. That rule is the reason the
 * photograph is not just an editable filename: the moment someone
 * attaches one is the only moment they know what it shows.
 */
const sheet = document.getElementById("sheet");
const palt = document.getElementById("palt");
const perr = document.getElementById("perr");
const pview = document.getElementById("pview");
const ptitle = document.getElementById("ptitle");
let pending = null;

function choose(fig) {
  const pick = document.createElement("input");
  pick.type = "file";
  pick.accept = "image/jpeg,image/png,image/webp";
  pick.addEventListener("change", () => {
    if (pick.files[0]) ask(fig, pick.files[0]);
  });
  pick.click();
}

function ask(fig, file) {
  pending = {fig, file};
  ptitle.textContent = file ? file.name : "Description";
  perr.textContent = "";
  palt.value = fig.dataset.alt || "";
  pview.removeAttribute("src");
  if (file) {
    const look = new FileReader();
    look.onload = () => pview.src = look.result;
    look.readAsDataURL(file);
  }
  sheet.hidden = false;
  palt.focus();
}

document.getElementById("pno").addEventListener("click", () => {
  sheet.hidden = true; pending = null; say("Nothing changed.");
});
sheet.addEventListener("click", (ev) => {
  if (ev.target === sheet) document.getElementById("pno").click();
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && !sheet.hidden) document.getElementById("pno").click();
});

document.getElementById("photo").addEventListener("submit", (ev) => {
  ev.preventDefault();
  if (!pending) return;
  const alt = palt.value.replace(/\s+/g, " ").trim();
  if (!alt) { perr.textContent = "A photograph needs a description."; palt.focus(); return; }

  const [kind, index] = pending.fig.dataset.photo.split(".");
  const done = (body, where) => {
    busy = true;
    sheet.hidden = true;
    say("Saving…");
    fetch(location.pathname + where, {method: "POST",
      headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})
      .then(r => r.json())
      .then(r => {
        if (!r.ok) { busy = false; say(r.message || "Refused.", true); return; }
        say(r.message || "Saved.");
        return settled(alt);
      })
      .catch(e => { busy = false; say(String(e), true); });
    pending = null;
  };

  /* No new file means the description alone changed, which is an
     ordinary field edit — `attach` would refuse it for having no
     photograph, and refusing to fix a description is not helpful. */
  if (!pending.file) {
    return done({kind, index: Number(index), field: "alt", value: alt}, "/edit");
  }

  const read = new FileReader();
  read.onload = () => done({
    kind, index: Number(index),
    filename: pending.file.name,
    /* The header is `data:<type>;base64,` — everything after the comma
       is the file. */
    data: String(read.result).split(",")[1],
    alt,
  }, "/attach");
  read.onerror = () => { perr.textContent = "That file could not be read."; };
  read.readAsDataURL(pending.file);
});

function edit(doc, el) {
  const was = el.textContent;

  /* Headings arrive split into one span per word, for the reveal.
     contenteditable over that is unusable — typing lands inside a
     clipping box and the caret disappears. Flatten first; the split
     comes back on the next load, which is a reload away. */
  if (el.classList.contains("split") || el.querySelector(".w")) {
    el.textContent = was;
    el.classList.remove("split");
  }

  const session = new AbortController();
  const opts = {signal: session.signal};

  el.contentEditable = "true";
  el.focus();
  doc.getSelection().selectAllChildren(el);
  say("Enter to keep it, Escape to leave it alone.");

  let over = false;
  const stop = (keep) => {
    if (over) return;             /* Enter then blur would run this twice */
    over = true;
    session.abort();              /* and nothing is left listening */
    el.contentEditable = "false";
    /* innerText, never innerHTML: anything pasted in arrives as markup
       otherwise, and the value is going into a line of TOML. */
    const now = el.innerText.replace(/\s+/g, " ").trim();
    if (!keep || !now || now === was.trim()) {
      el.textContent = was;
      say("Nothing changed.");
      return;
    }
    save(el.dataset.edit, now, was, el);
  };

  el.addEventListener("keydown", (k) => {
    if (k.key === "Enter") { k.preventDefault(); stop(true); }
    if (k.key === "Escape") { k.preventDefault(); stop(false); }
  }, opts);
  el.addEventListener("blur", () => stop(true), opts);
}

/* `kind.index.field` is an object; anything else is one of the page's
   own sentences. The key says which verb it needs, so the markup does
   not have to carry a second attribute saying the same thing. */
function save(key, value, was, el) {
  busy = true;
  const bits = key.split(".");
  const object = bits.length === 3;
  const where = location.pathname + (object ? "/edit" : "/text");
  const body = object
    ? {kind: bits[0], index: Number(bits[1]), field: bits[2], value}
    : {key, value};

  say("Saving…");
  fetch(where, {method:"POST", headers:{"Content-Type":"application/json"},
                body: JSON.stringify(body)})
    .then(r => r.json())
    .then(r => {
      if (!r.ok) { busy = false; el.textContent = was; say(r.message || "Refused.", true); return; }
      say(r.message || "Saved.");
      return settled(value);
    })
    .catch(e => { busy = false; el.textContent = was; say(String(e), true); });
}

/* WAIT FOR THE REBUILD, DO NOT GUESS AT IT.
   This was a 700ms timer, which is a bet on how long Zola takes. Lose
   the bet and the frame reloads the OLD page, so a saved edit looks
   lost until you reload by hand. Ask the site instead: fetch it until
   the new words are in it, then show it. */
function settled(value, tries = 0) {
  return fetch("/site/", {cache: "no-store"})
    .then(r => r.text())
    .then(html => {
      const there = html.includes(value
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"));
      if (there || tries > 25) {
        busy = false;
        view.contentWindow.location.reload();
        if (!there) say("Saved — the page is still rebuilding.", true);
        return;
      }
      return new Promise(go => setTimeout(go, 120)).then(() => settled(value, tries + 1));
    })
    .catch(() => { busy = false; view.contentWindow.location.reload(); });
}

view.addEventListener("load", arm);
if (view.contentDocument && view.contentDocument.readyState === "complete") arm();
</script>
</body></html>
"""


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
        if route not in {"edit", "add", "remove", "attach", "config", "text"}:
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

            if route == "text":
                message = set_text(str(body.get("key", "")),
                                   str(body.get("value", "")))
            elif route == "config":
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
