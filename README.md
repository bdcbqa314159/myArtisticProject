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

## Running it

```sh
./preview.sh        # or double-click preview.command
npx tsc             # after editing src/
npm test            # tsc + zola build + the drift check
```

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
