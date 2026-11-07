#!/usr/bin/env python3
"""A French draft to argue with, from DeepL.

    python3 tools/translate.py --draft          # fill every untranslated field
    python3 tools/translate.py --draft --only roles,intro
    python3 tools/translate.py --status         # what is still a machine draft
    python3 tools/translate.py --reviewed roles # this one has been read and kept

WHAT THIS IS FOR, AND WHAT IT IS NOT FOR.

The French page is not a translation of the English one. It is the
second version of the same site, for readers the client actually speaks
to, and he will write most of it himself — he is francophone and it is
his voice.

What a blank page costs is the reason this exists anyway: reacting to a
draft is far easier than starting from nothing, even in your own
language. "No, not that — this" is how direction works. So the output
here is a thing to disagree with, and the machinery below exists to stop
it being mistaken for a thing to publish.

NOTHING IT WRITES IS CONSIDERED DONE.

Every field it fills is listed in `content/_index.fr.drafts.txt`, the
same shape as the stand-in photograph ledger: a list, so that removing
them is a decision rather than a guess. While a key is in that file the
value is a machine draft, `tools/fr-check.py` says so, and the build
refuses to publish French.

The ledger is how a draft becomes reviewed: read it, change what is
wrong, take the key out. Nobody can do that by accident.

THE KEY NEVER REACHES A BROWSER.

The request is made here, in Python. The studio panel will eventually
have a button for this, and the button will call this code rather than
DeepL — so the key stays in this process, and the page's
`connect-src 'none'` stays as it is. A key in the page would be a key in
everyone's devtools.

THE BRAND IS NEVER SENT.

Filenames, fragment links, verification records and the trademark are
not prose and do not go over the wire. Translating them breaks the page,
falsifies a record, or improves a trademark.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import importlib.util                                        # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "fr_check", ROOT / "tools" / "fr-check.py")
fr = importlib.util.module_from_spec(_spec)                  # type: ignore[arg-type]
_spec.loader.exec_module(fr)                                 # type: ignore[union-attr]

ENV = ROOT / ".env"

# DeepL takes up to 50 texts in one request. The whole site is about a
# hundred strings, so this is two or three calls, not a hundred.
BATCH = 50


def key() -> "str | None":
    """The API key, from the environment or from .env — never from git.

    `.env` is already ignored. Nothing here prints the key, and the
    panel will never render it: a key that reaches a page reaches
    everyone who opens devtools on it.
    """
    found = os.environ.get("DEEPL_API_KEY", "").strip()
    if found:
        return found
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "DEEPL_API_KEY":
                return value.strip().strip('"').strip("'") or None
    return None


def endpoint(api_key: str) -> str:
    """Free keys end in `:fx` and live on a different host.

    DeepL's own convention. Overridable so the tests can point this at a
    local stand-in and exercise the request without a key or a network.
    """
    override = os.environ.get("DEEPL_API_URL", "").strip()
    if override:
        return override
    host = "api-free" if api_key.endswith(":fx") else "api"
    return f"https://{host}.deepl.com/v2/translate"


def translate(texts: "list[str]", api_key: str, formality: str) -> "list[str]":
    """One request, many strings, in order.

    `formality` is passed through rather than chosen here. French makes
    a register decision English does not — how close to the reader you
    stand — and that is the client's call about his own voice, not a
    default buried in a tool.
    """
    form: "list[tuple[str, str]]" = [
        ("target_lang", "FR"),
        ("source_lang", "EN"),
        # Keep the typography the page was written with. DeepL otherwise
        # normalises quotes and dashes, which undoes `smart_punctuation`.
        ("preserve_formatting", "1"),
    ]
    if formality != "default":
        form.append(("formality", formality))
    form += [("text", t) for t in texts]

    request = urllib.request.Request(
        endpoint(api_key),
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "myArtisticProject/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as answer:
        payload = json.loads(answer.read().decode("utf-8"))

    out = [t.get("text", "") for t in payload.get("translations", [])]
    if len(out) != len(texts):
        raise RuntimeError(
            f"asked for {len(texts)} translations and got {len(out)} — "
            "refusing to guess which is which"
        )
    return out


def write_ledger(keys: "list[str]") -> None:
    if keys:
        fr.LEDGER.write_text("".join(f"{k}\n" for k in sorted(set(keys))),
                          encoding="utf-8")
    elif fr.LEDGER.exists():
        fr.LEDGER.unlink()


def put(key_wanted: str, value: str) -> bool:
    """Write one translated value into the French page, in place.

    Surgical for the same reason every other writer here is: the file is
    mostly comments explaining why it looks as it does, and a serialiser
    would take all of them.
    """
    text = fr.FR.read_text(encoding="utf-8")
    parts = text.split("+++")
    if len(parts) < 3:
        return False
    fm = parts[1]

    for k, name, raw, _a, _b in fr.assignments(fm):
        if fr.is_list(raw):
            hit = [sub for sub, _n, _t in fr.list_entries(k, name, raw)
                   if sub == key_wanted]
            if not hit:
                continue
            rebuilt = fr.rebuild_list(
                k, name, raw,
                lambda sub, _n, english: value if sub == key_wanted else english)
            fm = fm.replace(f"{name} = {raw}", f"{name} = {rebuilt}", 1)
            break
        if k == key_wanted:
            fm = re.sub(
                rf'^{re.escape(name)}\s*=\s*".*"\s*$',
                f'{name} = "{value}"', fm, count=1, flags=re.M)
            break
    else:
        return False

    fr.FR.write_text("+++".join([parts[0], fm] + parts[2:]), encoding="utf-8")
    return True


def quote_safe(value: str) -> str:
    """TOML strings are double-quoted here, so a quote inside breaks one."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def draft(only: "list[str]", formality: str) -> int:
    api_key = key()
    if not api_key:
        print("\n  no DEEPL_API_KEY.\n")
        print("    Put it in .env, which git already ignores:\n")
        print("      DEEPL_API_KEY=your-key-here\n")
        print("    A free key covers this site many times over — the whole")
        print("    page is about four thousand characters against a")
        print("    500,000-a-month allowance.\n")
        return 1

    english = fr.fields(fr.front_matter(fr.EN))
    french = fr.fields(fr.front_matter(fr.FR))

    wanted = [
        k for k, (name, value) in french.items()
        if value == fr.PLACEHOLDER
        and name not in fr.COPIED and name not in fr.BRAND_FIELDS
        and k in english
    ]
    if only:
        wanted = [k for k in wanted if k in only or k.split("[")[0] in only]

    if not wanted:
        print("\n  nothing untranslated to draft.\n")
        return 0

    print(f"\n  drafting {len(wanted)} field(s) with DeepL "
          f"(formality: {formality})\n")

    done = fr.ledger_keys()
    filled = 0
    for start in range(0, len(wanted), BATCH):
        chunk = wanted[start:start + BATCH]
        sources = [english[k][1] for k in chunk]
        try:
            results = translate(sources, api_key, formality)
        except urllib.error.HTTPError as problem:
            # 456 is DeepL's "quota exceeded". Saying so beats "HTTP 456".
            why = {403: "the key was refused",
                   429: "too many requests — wait and try again",
                   456: "the monthly character quota is used up"}.get(
                       problem.code, f"HTTP {problem.code}")
            print(f"  stopped: {why}\n")
            break
        except (urllib.error.URLError, TimeoutError) as problem:
            print(f"  stopped: could not reach DeepL ({problem})\n")
            break
        except RuntimeError as problem:
            print(f"  stopped: {problem}\n")
            break

        for k, result in zip(chunk, results):
            if put(k, quote_safe(result)):
                done.append(k)
                filled += 1
                print(f"    {k}\n      {result}")

    write_ledger(done)
    print(f"\n  {filled} field(s) drafted. Every one is listed in")
    print(f"  {fr.LEDGER.relative_to(ROOT)} and counts as unreviewed.\n")
    print("  Read them, change what is wrong, then take the key out of")
    print("  that file — or: python3 tools/translate.py --reviewed <key>\n")
    return 0


def status() -> int:
    keys = fr.ledger_keys()
    if not keys:
        print("\n  no machine drafts awaiting review.\n")
        return 0
    french = fr.fields(fr.front_matter(fr.FR))
    print(f"\n  {len(keys)} machine draft(s) awaiting review:\n")
    for k in keys:
        value = french.get(k, ("", "<no longer in the page>"))[1]
        print(f"    {k}\n      {value}\n")
    return 0


def reviewed(keys: "list[str]") -> int:
    have = fr.ledger_keys()
    gone = [k for k in keys if k in have]
    if not gone:
        print("\n  none of those are machine drafts.\n")
        return 1
    write_ledger([k for k in have if k not in gone])
    print(f"\n  {len(gone)} marked as reviewed; "
          f"{len(have) - len(gone)} still to read.\n")
    return 0


def main(argv: "list[str]") -> int:
    def after(flag: str) -> "list[str]":
        if flag not in argv:
            return []
        at = argv.index(flag)
        return argv[at + 1].split(",") if at + 1 < len(argv) else []

    if "--status" in argv:
        return status()
    if "--reviewed" in argv:
        return reviewed(after("--reviewed"))
    if "--draft" in argv:
        formality = (after("--formality") or ["default"])[0]
        if formality not in {"default", "prefer_more", "prefer_less"}:
            print(f"\n  unknown formality {formality!r} — "
                  "default, prefer_more or prefer_less\n", file=sys.stderr)
            return 1
        return draft(after("--only"), formality)

    print(__doc__.split("WHAT THIS IS FOR")[0].strip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
