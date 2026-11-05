# Brand marks — where each file came from

Four files, two per service, every one downloaded from the owner's own
brand page and copied in byte-for-byte.

| file | as named in the owner's download package |
|---|---|
| `linkedin-black.png` | `in-logo / InBug-Black.png` |
| `linkedin-white.png` | `in-logo / InBug-White.png` |
| `whatsapp-black.svg` | `01_Glyph / 01_Digital RGB / 03_SVG / Digital_Glyph_Black_RGB_2026.svg` |
| `whatsapp-white.svg` | `01_Glyph / 01_Digital RGB / 03_SVG / Digital_Glyph_White_RGB_2026.svg` |

| service | package | obtained |
|---|---|---|
| LinkedIn | Brand Resources → the In Bug | 2026-11-05 |
| WhatsApp | Brand Resource Center Page Downloads | 2026-11-05 |

Not from an icon pack, not from a search result, not redrawn. Icon
archives are overwhelmingly unlicensed re-uploads, and a redrawn
approximation is a worse position than the real mark: still a use of the
trademark, minus the permission the download grants.

## Unmodified, and checkable

    b80ab65537aad1b5013da98fe82d1c36c1bb4ca896fe7829a880cc5f307693ca  linkedin-black.png
    ed22a5ab46c171e3449708ff34923de7298da00ac204c7f85444db05bf888791  linkedin-white.png
    dea0d50de5d2e53320246d7172a2b8e84a999caa7798cd91681e63831cba6ed9  whatsapp-black.svg
    7fb054c0f4bea644b4a4a014d6d8581aad7e6dcb639049d17a578dc44f8e6fd4  whatsapp-white.svg

Run `shasum -a 256 static/img/brand/*` against the owner's package before
assuming these are still untouched. Nothing here has been through an
optimiser — an SVG minifier would change the bytes, and then this table
would be a claim nobody can test.

## Why two of each

The footer has four background states: the cool and cream palettes, each
light and dark. No single file is legible on all four. Both owners
publish a black and a white variant for precisely this situation, so the
pair is **their** artwork in **their** colours — it is not a recolour,
which would not be allowed.

`templates/index.html` swaps them with a `<picture>` and
`media="(prefers-color-scheme: dark)"` — the browser's own mechanism, no
script. The site's dark palette comes from the same media query, so the
mark and the page can never disagree.

The colour variants exist too (LinkedIn blue, WhatsApp green) and are
equally permitted. They were tried and set aside: WhatsApp's glyph is an
outline and LinkedIn's bug is a solid block, so side by side in colour
the blue dominates the green. Monochrome reads as a pair.

## Three conditions travel with them

1. **Used as published.** Scaled, and nothing else. Never recoloured,
   stretched, masked, outlined, boxed or redrawn. `site.css` sets
   `height` and leaves `width: auto`, deliberately: the two marks are not
   the same shape, and pinning both dimensions would stretch one of them.
2. **Each links to our own presence.** The client's LinkedIn profile and
   the client's WhatsApp Business number. A mark pointed at
   `linkedin.com` is decoration, which the terms do not allow —
   `tools/content-check.py` rejects it.
3. **From the owner, for this site.** If either brand page changes its
   artwork or its terms, the files here are stale: re-download rather
   than edit.
