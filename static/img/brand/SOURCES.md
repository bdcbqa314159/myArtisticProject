# Brand marks — where each file came from

Two files are expected here, and neither may be committed until it has
been downloaded from the owner's own brand page:

| file | download from | licence granted by |
|---|---|---|
| `linkedin.svg` | <https://brand.linkedin.com/downloads> — the "In" bug | accepting LinkedIn's brand terms at download |
| `whatsapp.svg`  | <https://whatsapp.com/brand> — the glyph | accepting WhatsApp's brand terms at download |

Not from an icon pack, not from a search result, not redrawn. Icon
archives are overwhelmingly unlicensed re-uploads, and a redrawn
approximation is a worse position than the real mark: it is still a use
of the trademark, minus the permission the download grants.

## Three conditions travel with them

1. **Used as published.** Sized, and nothing else. Never recoloured,
   stretched, masked, outlined, boxed or redrawn. `site.css` touches
   `width` and `height` on `.dock img` and deliberately nothing more.
2. **Each links to our own presence.** The client's LinkedIn profile and
   the client's WhatsApp Business number. A mark pointed at
   `linkedin.com` is decoration, which the terms do not allow —
   `tools/content-check.py` rejects it.
3. **From the owner, for this site.** If either brand page changes its
   artwork or its terms, the file here is stale: re-download rather than
   edit.

When a file lands, record the date and the exact asset name below.

| file | asset as named on the brand page | obtained |
|---|---|---|
| `whatsapp.svg` | `01_Glyph / 01_Digital RGB / 03_SVG / Digital_Glyph_Green_RGB_2026.svg`, from the Brand Resource Center download package | 2026-11-05 |
| `linkedin.svg` | — still needed | — |

`whatsapp.svg` is byte-identical to the file in that package:

    sha256  f7b1311db718533e671645f57cd94b92f0e006e61d7e6581a80675fc5a478fc4

Re-run `shasum -a 256` against the source before assuming it is still
untouched. The package also ships Black and White glyphs for monochrome
contexts; we use Green because the footer has four background states
(cool and cream, each light and dark) and Green is the only single file
that is legible in all of them. Switching to the monochrome pair is a
`<picture>` element and a second filename, not a recolour — never a
recolour.
