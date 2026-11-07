#!/usr/bin/env python3
"""A complete set of stand-in content, so the drop-in folder starts full.

Used by `tools/dropin.py --init`. Not meant to be run on its own.

WHY A FULL SET AND NOT EMPTY SLOTS.

An empty `_dropin/` is a folder of instructions. What is actually wanted
is a site that already works, so that replacing one photograph shows
what one photograph does — rather than needing six references, three
concepts, five legal fields and a film before anything can be judged at
all.

So this writes a site that passes every gate the published one has to
pass: six verified references, a contact address, a complete legal
notice, photographs, a showreel. Swap pieces out one at a time and watch
the real thing arrive.

WHY IT IS DERIVED, NOT STORED.

The content file here is made by FILLING IN the repository's own
`content/_index.md`, not by keeping a copy of it. A stored copy drifts:
a field added to the schema tomorrow would be missing from the fixture
and nobody would notice until the fixture quietly stopped exercising it.
Filling in the real file means the fixture always has exactly the fields
the site has.

EVERY VALUE IS OBVIOUSLY NOT REAL.

"Test Organisation 01", "sample-fixture, not a real record". The brief
forbids inventing references, roles, dates and credits, and although
this folder is git-ignored and never published, content that could be
mistaken for the client's would be one careless copy away from the
thing the rule exists to prevent. Nothing here reads as a credential.
"""

import concurrent.futures
import re
import shutil
import struct
import subprocess
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# The site's own tokens, so the fixture looks like the site rather than
# like a test harness bolted to it.
INK, MUTED, BG, PANEL = "#eef1f5", "#9aa3b0", "#101317", "#171b21"

WORK = [
    ("Test Organisation 01", "A sample engagement, written to fill this slot.",
     "Sample Role — Creative Direction"),
    ("Test Organisation 02", "A sample engagement, written to fill this slot.",
     "Sample Role — Artistic Direction"),
    ("Test Organisation 03", "A sample engagement, written to fill this slot.",
     "Sample Role — Programming"),
    ("Test Organisation 04", "A sample engagement, written to fill this slot.",
     "Sample Role — Experience Design"),
    ("Test Organisation 05", "A sample engagement, written to fill this slot.",
     "Sample Role — Workshop Lead"),
    ("Test Organisation 06", "A sample engagement, written to fill this slot.",
     "Sample Role — Partnership Development"),
]

CONCEPTS = [
    "Sample Format One", "Sample Format Two", "Sample Format Three",
]

CONFIG_FILL = {
    "extra.real": {
        "name": "TEST STUDIO",
        "person": "A. Sample",
        "title": "TEST STUDIO — fixture content, not a real site",
        "approach_lead": "Sample text standing in for the artist's own "
                         "account of how a project begins.",
        "about_lead": "Sample text standing in for the artist's own "
                      "account of their practice.",
    },
    "extra.contact": {
        "email": "sample@test.invalid",
        "vcard_name": "A. Sample",
        "vcard_role": "Artist & Creative Director (sample)",
        "vcard_org": "TEST STUDIO",
        "vcard_phone": "+33 1 00 00 00 00",
        "vcard_url": "https://test.invalid",
    },
    "extra.legal": {
        "entity": "TEST STUDIO (fixture)",
        "status": "Entrepreneur individuel (sample)",
        "registration": "SIRET 000 000 000 00000 (sample)",
        "address": "0 rue de l'Exemple, 00000 Sample, France",
        "publisher": "A. Sample",
    },
}


def card(label: str, index: str, portrait: bool) -> str:
    """One stand-in photograph, as a page Chrome can render."""
    w, h = (1067, 1600) if portrait else (1600, 1067)
    return f"""<meta charset=utf-8><style>
html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden}}
body{{background:linear-gradient(145deg,{PANEL} 0%,{BG} 55%,#0b0d10 100%);
 color:{INK};display:flex;flex-direction:column;align-items:center;
 justify-content:center;gap:28px;
 font:400 16px/1.4 "Iowan Old Style",Palatino,Georgia,serif}}
.k{{font-size:22px;letter-spacing:.3em;text-transform:uppercase;color:{MUTED}}}
.n{{font-size:{220 if not portrait else 180}px;line-height:.9;margin:0;
 font-weight:400;letter-spacing:-.03em}}
.s{{font-size:24px;color:{MUTED}}}
</style>
<span class=k>{label}</span>
<p class=n>{index}</p>
<span class=s>stand-in image · {w}×{h}</span>"""


def render(html: str, dest: Path, scratch: Path) -> bool:
    """HTML -> PNG -> JPEG, with no network and no stock photography.

    Generated rather than downloaded on purpose: a fixture that reaches
    the internet fails on a train, and a fixture built from somebody
    else's photographs is the thing NOTICE forbids, in a folder that
    makes it easy to forget where they came from.
    """
    if not Path(CHROME).exists() or not shutil.which("sips"):
        return False
    page = scratch / "card.html"
    page.write_text(html, encoding="utf-8")
    size = re.search(r"width:(\d+)px;height:(\d+)px", html)
    w, h = (size.group(1), size.group(2)) if size else ("1600", "1067")
    png = scratch / "card.png"
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         f"--window-size={w},{h}", "--virtual-time-budget=3000",
         f"--screenshot={png}", page.as_uri()],
        capture_output=True,
    )
    if not png.exists():
        return False
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "72",
         str(png), "--out", str(dest)],
        capture_output=True,
    )
    png.unlink(missing_ok=True)
    return dest.exists()


# How many projects each reference carries, and how many photographs
# each of those carries.
#
# TWO TO FOUR PROJECTS. On a 390px phone four thumbnails are two clean
# rows; beyond that a reference stops reading as a curated selection and
# starts reading as a contact sheet, which is the opposite of the point.
# Two is allowed and has to look deliberate rather than unfinished.
#
# FOUR TO SIX PHOTOGRAPHS. Enough to be worth a swipe, few enough to
# reach the end of.
#
# Uneven on purpose: a tidy grid hides every layout problem there is.
SHAPE = [
    [5, 4, 6, 4],         # reference 1 — four projects
    [4, 6, 5],
    [6, 4, 5, 4],
    [5, 6],               # two is allowed, and must still look deliberate
    [4, 5, 6],
    [6, 4, 5, 4],
]


def png(w: int, h: int, hue: int) -> bytes:
    """A gradient panel, written by hand.

    Pure Python because there are about a hundred of these. Rendering
    each one in a browser the way the six reference images are rendered
    would take minutes on every `--init`, and a fixture nobody waits for
    is a fixture nobody uses. No Pillow either: one more thing to
    install is one more reason the drop-in folder does not work on
    somebody's machine.
    """
    # BANDS, not pixels. A pixel loop over 1400x933 is four million
    # byte appends, and ninety-four of those took thirty-eight seconds —
    # long enough that nobody would run `--init` twice. Sixteen distinct
    # rows, each repeated, is the same picture to the eye and about two
    # hundred times less work.
    BANDS = 16
    rows = bytearray()
    for band in range(BANDS):
        down = band / BANDS
        row = bytearray(b"\x00")                  # filter: none
        for x in range(w):
            t = (x / w) * 0.6 + down * 0.4
            row += bytes((
                int(16 + hue * 0.35 + t * 46),
                int(19 + (hue % 60) * 0.28 + t * 52),
                int(23 + (hue % 97) * 0.22 + t * 64),
            ))
        rows += bytes(row) * (h // BANDS + (1 if band < h % BANDS else 0))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
            + chunk(b"IEND", b""))


def fetch(url: str) -> "bytes | None":
    try:
        with urllib.request.urlopen(url, timeout=20) as answer:
            data = answer.read()
        # A truncated download that still "succeeds" is a broken image
        # nobody notices until it is on a phone in front of a client.
        return data if len(data) > 10_000 else None
    except Exception:                                       # noqa: BLE001
        return None


def photographs(wanted: "list[tuple[Path, int, int, str]]") -> "set[Path]":
    """Real photographs for the fixture, from Lorem Picsum.

    The same source `tools/placeholders.py` already uses, for the same
    reason: Unsplash photography under the Unsplash License — free use,
    no permission, no attribution required. Generated panels prove the
    layout works; actual photographs are the only way to see whether it
    LOOKS like a portfolio, which is what the client asked for.

    SEEDED, not random. The same request returns the same photograph, so
    a layout reviewed yesterday is the layout reviewed today.

    Offline it quietly falls back to the drawn panels — a fixture that
    needs the internet is a fixture that fails on a train.
    """
    got: "set[Path]" = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {
            pool.submit(fetch, f"https://picsum.photos/seed/{seed}/{w}/{h}"): dest
            for dest, w, h, seed in wanted
        }
        for job in concurrent.futures.as_completed(jobs):
            dest = jobs[job]
            data = job.result()
            if data:
                dest.write_bytes(data)
                got.add(dest)
    return got


def projects(content: Path, real: bool = True) -> "tuple[list[str], list[dict], list[dict]]":
    """Several projects per reference, several photographs per project."""
    made: "list[str]" = []
    rows: "list[dict]" = []
    shots: "list[dict]" = []
    letters = "abcdefghij"

    wanted: "list[tuple[Path, int, int, str]]" = []
    plan: "list[tuple[Path, int, int, int, str, str]]" = []

    for ref, counts in enumerate(SHAPE, 1):
        for slot, how_many in enumerate(counts):
            pid = f"r{ref}-{letters[slot]}"
            rows.append({"id": pid, "reference": ref,
                         "name": f"Projet {ref}-{letters[slot].upper()}"})
            for n in range(1, how_many + 1):
                name = f"{pid}-{n:02d}.jpg"
                # Upright now and then, as a real set is.
                tall = (n % 4 == 0)
                w, h = (900, 1200) if tall else (1400, 933)
                dest = content / name
                # The seed names nothing and nobody. An earlier set used
                # the client's own mark in its seeds, in a public
                # repository — see the brand tripwire in content-check.
                seed = f"folio-{ref}{slot}{n}"
                hue = (ref * 37 + slot * 13 + n * 7) % 120
                plan.append((dest, w, h, hue, name, f"{ref}-{letters[slot].upper()}"))
                wanted.append((dest, w, h, seed))

    got = photographs(wanted) if real else set()

    for dest, w, h, hue, name, label in plan:
        if dest not in got:
            dest.write_bytes(png(w, h, hue))
        made.append(name)
        shots.append({"project": name.rsplit("-", 1)[0], "file": name,
                      "alt": (f"Photographie {name[-6:-4]} du projet {label} — "
                              "une image de remplacement, pas le travail du client")})

    return made, rows, shots


def images(content: Path, scratch: Path) -> list[str]:
    made = []
    for i in range(1, 7):
        name = f"work-{i:02d}.jpg"
        portrait = i == 4          # one upright, as the real set has
        if render(card("Selected work", f"{i:02d}", portrait),
                  content / name, scratch):
            made.append(name)
    return made


def showreel(video_dir: Path, scratch: Path) -> list[str]:
    """A real MP4, so the player is exercised rather than described."""
    if not shutil.which("ffmpeg"):
        return []
    frame = scratch / "reel.png"
    page = scratch / "reel.html"
    page.write_text(f"""<meta charset=utf-8><style>
html,body{{margin:0;height:100%}}
body{{background:{BG};color:{INK};display:flex;flex-direction:column;
 align-items:center;justify-content:center;gap:18px;
 font:400 16px/1.4 "Iowan Old Style",Palatino,Georgia,serif}}
.k{{font-size:13px;letter-spacing:.24em;text-transform:uppercase;color:{MUTED}}}
h1{{font-size:62px;margin:0;font-weight:400;letter-spacing:-.02em}}
p{{margin:0;color:{MUTED};font-size:19px}}
</style>
<span class=k>Showreel</span><h1>Stand-in film</h1>
<p>Replace with the real showreel — _dropin/static/video/</p>""",
                    encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         "--window-size=1280,720", "--virtual-time-budget=3000",
         f"--screenshot={frame}", page.as_uri()],
        capture_output=True,
    )
    if not frame.exists():
        return []
    mp4 = video_dir / "showreel.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(frame), "-t", "6",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-r", "25", "-vf", "scale=1280:720", str(mp4)],
        capture_output=True,
    )
    poster = video_dir / "poster.jpg"
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                    str(frame), "--out", str(poster)], capture_output=True)
    frame.unlink(missing_ok=True)
    return [p.name for p in (mp4, poster) if p.exists()]


def blocks_for(rows: "list[dict]", shots: "list[dict]") -> str:
    """The projects and their photographs, as TOML to paste in."""
    out = ["", "# ---- the work inside each reference ---------------------------------",
           "# Generated by tools/dropin_samples.py. Flat and related by id, which",
           "# is what lets objects.py and the studio panel go on addressing an",
           "# object as kind/index/field without learning to nest.", ""]
    for row in rows:
        out += ["[[extra.project]]",
                f'id = "{row["id"]}"',
                f'reference = {row["reference"]}',
                f'name = "{row["name"]}"', ""]
    for shot in shots:
        out += ["[[extra.photo]]",
                f'project = "{shot["project"]}"',
                f'file = "{shot["file"]}"',
                f'alt = "{shot["alt"]}"', ""]
    return "\n".join(out)


def fill_content(source: str, have_images: bool, have_video: bool,
                 rows: "list[dict] | None" = None,
                 shots: "list[dict] | None" = None) -> str:
    """The repository's own content file, with every placeholder answered."""
    out = source

    # --- the six references ------------------------------------------
    # Rebuilt one block at a time so the fixture inherits whatever fields
    # the schema carries today, rather than a copy frozen last week.
    index = {"n": 0}

    def reference(match: "re.Match[str]") -> str:
        block = match.group(0)
        i = index["n"]
        index["n"] += 1
        if i >= len(WORK):
            return block
        name, text, role = WORK[i]

        def put(field: str, value: str, body: str) -> str:
            line = f'{field} = {value}'
            if re.search(rf'^{field}\s*=', body, re.M):
                return re.sub(rf'^{field}\s*=.*$', line, body, count=1, flags=re.M)
            return body.rstrip("\n") + f"\n{line}\n"

        block = put("name", f'"{name}"', block)
        block = put("text", f'"{text}"', block)
        block = put("role", f'"{role}"', block)
        block = put("verified", "true", block)
        block = put("verified_on", '"2026-11-05"', block)
        block = put("evidence", '"sample-fixture, not a real record"', block)
        if have_images:
            block = put("image", f'"work-{i + 1:02d}.jpg"', block)
            block = put(
                "alt",
                f'"Stand-in image {i + 1:02d} — a generated panel, not a photograph"',
                block,
            )
        return block

    out = re.sub(r"\[\[extra\.work\]\](?:(?!\n\[\[|\n# ----).)*",
                 reference, out, flags=re.S)

    # --- the three concepts -------------------------------------------
    spot = {"n": 0}

    def concept(match: "re.Match[str]") -> str:
        block = match.group(0)
        i = spot["n"]
        spot["n"] += 1
        if i >= len(CONCEPTS):
            return block
        block = re.sub(r'^name\s*=.*$', f'name = "{CONCEPTS[i]}"',
                       block, count=1, flags=re.M)
        return re.sub(
            r'^text\s*=.*$',
            'text = "Sample description standing in for an original format."',
            block, count=1, flags=re.M)

    out = re.sub(r"\[\[extra\.concepts\]\](?:(?!\n\[\[|\n# ----).)*",
                 concept, out, flags=re.S)

    if rows:
        # After the references and before the concepts, so the file reads
        # in the order the page does.
        mark = "# ---- 04 original concepts"
        if mark in out:
            out = out.replace(mark, blocks_for(rows, shots or []) + "\n" + mark, 1)
        else:
            out += blocks_for(rows, shots or [])

    if have_video:
        out = re.sub(r'^video\s*=.*$', 'video = "video/showreel.mp4"',
                     out, count=1, flags=re.M)
        out = re.sub(r'^poster\s*=.*$', 'poster = "video/poster.jpg"',
                     out, count=1, flags=re.M)

    return out


def fill_config(source: str) -> str:
    out = source

    # THE FIXTURE RUNS AS THE LAUNCH CONFIGURATION.
    #
    # `live` decides which identity the page wears — the public demo one
    # or the client's — and it also takes away the palette toggle and
    # the stand-in badges. False, the fixture would be a complete set of
    # content rendered as a demo, which is the one thing it is not for.
    #
    # Safe here and only here: this file is `_dropin/config.toml`, which
    # git ignores and nothing publishes. The tracked `config.toml` stays
    # false, and the panel still refuses to touch it — whether the site
    # MAY go live is a question for the gate, whether it DOES is a
    # person's decision with the repository in front of them.
    out = re.sub(r'^live\s*=\s*false', "live = true", out, count=1, flags=re.M)
    for section, fields in CONFIG_FILL.items():
        header = re.search(rf"^\[{re.escape(section)}\]\s*$", out, re.M)
        if not header:
            continue
        start = header.end()
        nxt = re.search(r"^\[", out[start:], re.M)
        end = start + (nxt.start() if nxt else len(out[start:]))
        block = out[start:end]
        for key, value in fields.items():
            # The trailing comment is kept — in config.toml it is often
            # the only thing saying what the field is for.
            block = re.sub(
                rf'^({re.escape(key)}\s*=\s*)"[^"]*"([ \t]*#.*)?$',
                lambda m: f'{m.group(1)}"{value}"{m.group(2) or ""}',
                block, count=1, flags=re.M)
        out = out[:start] + block + out[end:]
    return out
