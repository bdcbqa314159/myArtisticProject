# The content objects

The page is assembled from objects. To add a project, a capability or
a concept, drop a block into `content/_index.md` — no template is
touched, nothing is positioned by hand, and the section grows by
itself.

```sh
python3 tools/objects.py --add reference   # prints a block to paste
python3 tools/objects.py                   # checks every object
```

Both run in CI. A required field left empty, or a field name
misspelt, fails the build — a misspelt field is otherwise ignored in
silence, which is the worst failure available: the page looks fine
and the value is simply gone.

**Generated from `tools/objects.py`. Do not edit by hand.**

## reference

`[[extra.work]]` — One organisation worked with, and the role held there. The six of them are ordered by widening discipline, and the order is the argument: a practice developing, not six credentials side by side.

| field | required | |
|---|---|---|
| `name` | yes | the organisation, as it writes its own name |
| `domain` | yes | the territory, as "A × B" — Sport × Culture |
| `text` | yes | one sentence on what the work was |
| `role` | yes | the role held, exactly. Never rounded up |
| `verified` | yes | true only once the role has been checked against the record |
| `verified_on` | no | the day it was checked, YYYY-MM-DD. Required when verified |
| `evidence` | no | what it was checked against. Required when verified |
| `image` | no | a file in content/, e.g. project-01.jpg |
| `alt` | no | what the photograph shows, for someone who cannot see it. Required when there is an image |

## capability

`[[extra.services]]` — One way of working together. Read as a group, so they should be the same size as each other.

| field | required | |
|---|---|---|
| `name` | yes | the capability, three or four words |
| `text` | yes | one sentence. No claim the rest of the page does not support |

## concept

`[[extra.concepts]]` — An original format. NOT a completed commission, and the status is what keeps that distinction visible.

| field | required | |
|---|---|---|
| `status` | yes | where it stands — "In development", "Opportunity area" |
| `name` | yes | the format's name |
| `text` | yes | one sentence on what it is |

## pillar

`[[extra.about_pillars]]` — One strand of the practice, in About.

| field | required | |
|---|---|---|
| `name` | yes | the strand |
| `text` | yes | a phrase, not a sentence — these sit in a narrow column |
