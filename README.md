# myArtisticProject

A one-page landing site. Same manner as **myBureau**: Zola builds it,
TypeScript moves it, and the browser downloads no library to run it.

---

## The stack

| layer | what | why this one |
|---|---|---|
| site | **Zola** 0.23 (one binary, `brew install zola`) | templates + Markdown + build-time image resizing, no `node_modules` on the client's machine |
| content | **Markdown in `content/`** | the client edits text in a text editor; the filesystem is the CMS |
| style | **plain CSS**, one file | custom properties are the theming layer; no preprocessor to install |
| motion | **TypeScript**, compiled by `tsc` | one file, no bundler, no runtime dependency |
| checks | `tsc --noEmit`, `zola build`, `tools/js-is-current.sh` | both must be clean before pushing |

Zero runtime dependencies on the frontend is a **constraint**, not a
preference — the same one myBureau holds.

### Do we need Rust?

No. Rust is already in the stack — `zola` is a Rust binary — but there is
no Rust *source* here and there does not need to be.

What runs in the browser is TypeScript, and TypeScript reaches everything
a landing page's motion needs:

- **CSS does most of it.** Transitions, transforms, `text-wrap: balance`,
  `color-scheme`. Composited by the GPU, off the main thread, free.
- **TypeScript decides *when*.** `IntersectionObserver` for scroll
  reveals — see `src/landing.ts`. Twelve lines, every browser.
- **Canvas for anything painted.** The hero wash is four drifting
  gradients at 60 fps and costs fill rate, not arithmetic.
- **WebGL when it is genuinely per-pixel** — displacement, fluid,
  raymarching. That is a fragment shader (GLSL) called from the same
  TypeScript file. Still no Rust.

WASM — compiled from Rust or anything else — earns its place when a
single frame needs *millions* of arithmetic operations that cannot be
expressed as a shader: a physics solver, mesh generation, video decoding.
A landing page is not that, and the cost of pretending otherwise is a
toolchain the client cannot install and a megabyte they have to download.

If a brief ever does ask for that, the upgrade path is marked in
`src/landing.ts` and it is a shader, not a language.

---

## Layout

```
config.toml          one language, two names, a live/not-live switch
content/_index.md    front matter = the hero; body = the page
templates/index.html the only template
static/css/site.css  the only stylesheet — colours are five tokens at the top
static/js/landing.js compiled, committed (see below)
src/landing.ts       the only script
preview.command      double-click this
```

## Adding content

The page is assembled from objects — a project, a capability, a concept.
Adding one is dropping a block into `content/_index.md`; no template is
touched and the section grows by itself.

```sh
python3 tools/objects.py --add reference   # prints a block to paste
python3 tools/objects.py                   # checks every object
```

See **[OBJECTS.md](OBJECTS.md)** for every object and its fields. That
file is generated from `tools/objects.py`, which is also what the build
enforces, so the documentation cannot drift from the rules.

## Running it

```sh
npm run deployed            # did what we merged actually reach the site?
./preview.sh                # the placeholder site — or double-click preview.command
python3 tools/dropin.py --serve   # the same site with the REAL content
npx tsc                     # after editing src/
npm test                    # tsc + zola build + the drift check
python3 tools/fr-check.py   # has the French page kept up with the English one?
python3 tools/translate.py --draft    # a French draft from DeepL, to argue with
```

### Two previews, and why

`./preview.sh` serves the tracked tree: placeholders, no real name, the
version that gets published.

`tools/dropin.py` serves the real thing. The client's names, photographs
and showreel go in `_dropin/`, which is git-ignored; the script lays them
over a copy of the tree in `_local/`, which is also ignored, and serves
that. **Nothing it does touches a tracked file, and there is no flag to
make it.** That is the mechanism keeping his material out of a public
repository — not a habit, and not a reviewer noticing.

`_local/` is an ordinary checkout, so every tool already here works
inside it unchanged: the studio panel, `objects.py`, and the same
`content-check.py` gate — pointed at the version with the real names in.

```sh
python3 tools/dropin.py --init    # create _dropin/, full of stand-in content
python3 tools/dropin.py           # assemble, and list what is still missing
```

`--init` starts it **full**: six verified references, three concepts, a
contact, a complete legal notice, six generated images and a real MP4
showreel — enough that the site passes every gate it would have to pass
to go live, and runs as the launch configuration rather than the demo.
Replace a piece at a time and watch the real thing arrive. Nothing in it
is real, nothing came from anyone else's camera, and the generator needs
no network. `--init --bare` gives empty slots instead.

## The French page

It is not a translation of the English one — it is the second version of
the same site, for the readers the client actually speaks to, and he
writes it. `tools/fr-check.py` guarantees the two pages have the same
**fields**, never the same words, and fails the build if either side
gains or loses one. That comparison exists because its absence let the
French file fall thirty-six fields behind without anyone noticing.

`tools/translate.py --draft` fills the untranslated fields from DeepL.
Not to publish — to argue with: a blank page is harder to answer than a
wrong one, even in your own language. Everything it writes is listed in
`content/_index.fr.drafts.txt` and counts as unread; while that file has
anything in it the page stays a draft and Zola does not build it.

Needs `DEEPL_API_KEY` in `.env`, which git already ignores. The request
is made in Python, so the key never reaches a browser and the page's
`connect-src 'none'` stays as it is. The brand, filenames, fragment
links and verification records are never sent.

## Why the compiled JS is in the repo

`static/js/landing.js` is committed, which is unusual and deliberate: it
is the difference between the client needing Node, npm and a build step
to look at their own site, and needing none of them. The bargain only
holds if the output never drifts from `src/`, which is what
`tools/js-is-current.sh` is for.

## Not live yet

`live = false` in `config.toml` sets `noindex, nofollow` and carries no
real name, so the placeholder content misrepresents nobody. Flip it when
the real name and the real assets are both in.

## Client material

Anything the client sends goes in `_client_input/` or `_ref/` — both
git-ignored, along with `specs/`, because the spec quotes the brief and
names the client. It is theirs, not ours to publish.

The brand shown here, **10MILES**, is a stand-in. The client's own mark
is a registered trademark and this repository is public, so no real
name, organisation, role or format appears in any tracked file. See
NOTICE, and `tools/content-check.py`, which enforces it.
