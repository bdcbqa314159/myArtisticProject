+++
title = "10MILES"
template = "index.html"

# ---------------------------------------------------------------------
# THE PAGE, AS DATA.
#
# STRUCTURE HERE, NAMES AT HANDOVER.
#
# The client's brand is an established trademark and this repository is
# public, so no real name, organisation, role or format description is
# written in this file — a committed file is readable whatever the page
# chooses to render.
#
# What stays is everything that identifies nobody: the section order,
# the editorial copy about ways of working, and the generic domains.
# What leaves arrives at handover, into a checkout that is not this one.
#
# Nothing here is invented either: a missing value says it is missing.
# No company, role, date or credit is ever written to fill a gap.
# See NOTICE.
#
# ---------------------------------------------------------------------
# THE VOICE: FIRST PERSON SINGULAR.
#
# Maquette V2 moved the positioning from a production company to an
# artist and creative director, but it did not finish the job — the copy
# still mixes "I bring…", "We develop…" and "the artist develops…"
# across the eight sections. Three grammatical persons on a page whose
# whole purpose is to read as one person's authorship.
#
# The rule here: **I**, everywhere a human is speaking.
#
# Two deliberate exceptions, both of which are not a human speaking:
#   - the ENTITY, in legal and partnership lines. "Professional
#     references above do not imply that each organisation is a
#     contracted partner" is about the company, not the person.
#   - the INCLUSIVE "we", meaning you-and-I. "How we can work together"
#     is an invitation, not a corporate plural, and changing it to "I"
#     would make it a boast.
#
# Needs the client's ratification. It is reversible in three strings.
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------

[extra]
issue = "Issue 01 — 2026"
place = "France · International"

eyebrow = "Artist-led creative direction · International collaborations"
roles = "Artist. Creative Director. Experience Designer. Creating across culture, movement, sport and live performance."
intro = "I bring artistic vision, multidisciplinary experience and the right collaborators together to shape ideas into live experiences."

cta_work = "Explore selected work"
cta_contact = "Let's talk"

approach_title = "Ideas become experiences."
showreel_label = "Showreel"
showreel_spec = "16:9 · 60–90 seconds"
video = ""
poster = ""
services_title = "How we can work together."
work_title = "Experience behind the ideas."
work_lead = "Organisations I have worked with, and the roles I held. Each can be expanded with verified media, dates, credits and deliverables."
work_note = "Professional references above do not imply that each organisation is a contracted partner."
concepts_title = "Formats in development."
concepts_lead = "Original ideas designed to evolve through partnerships and pilot projects. These are development concepts, not completed client commissions."
# Two phrases, because the client asked for them to exchange places
# visibly, once, as the section arrives — newFeedBack01 point 4. They are
# the halves of one sentence and stay one field, so there is nothing for
# a second copy to disagree with.
#
# Exactly two → they swap. One, or three, or none → the heading renders
# as written and nothing moves. The effect is a property of the content's
# shape rather than a switch somebody has to remember to set.
ecosystem_title = ["Independent by design.", "Collaborative by nature."]
ecosystem_lead = "I draw on cross-sector experience and a professional network spanning artistic creation, performance, sport, cultural venues, education and media. I shape creative collaborations around each project, with production handled by the right partners."
about_title = "Built on practice. Open to new territories."
about_text = "Working across artistic and operational roles helps me connect creative ambition with the realities of delivery. Through 10MILES I develop concepts and international collaborations, with a priority market abroad."
contact_title = "Let's build something together."
contact_lead = "For creative direction, experience design, original concepts and collaborations."

# ---- the form behind "Let's talk" -----------------------------------
# Every word it can say, here rather than in the script, so the French
# page carries its own and tools/fr-check.py can see them.
form_title = "Let's talk."
form_lead = "Tell me what you are making, and where it is going."
form_mail = "Your email"
form_subject = "Subject"
form_message = "Your message"
form_send = "Send"
form_cancel = "Not now"
form_privacy = "Your message reaches an inbox. It is not stored anywhere else, and the address is used only to reply."
form_sending = "Sending…"
form_sent = "Sent. Thank you — you will have a reply."
form_failed = "That did not send. Try again in a moment."
form_offline = "The form is not connected yet. No message was sent."
err_mail_missing = "An email address, so there is somewhere to reply."
err_mail_invalid = "That address does not look like one."
err_mail_long = "That address is longer than an address can be."
err_mail_one = "One address, please."
err_subject = "The subject has something in it that cannot be sent."
err_message_missing = "A message, however short."
err_message_long = "That is longer than the form accepts."
err_message_bad = "The message has something in it that cannot be sent."
err_message_links = "That is a lot of links. Say it in words and I will ask."
contact_copy = "Copy introduction"
contact_save = "Save contact"
ecosystem_fields = [
  "Artists & Performers",
  "Creative Producers",
  "Sport & Movement",
  "Cultural Venues",
  "Education & Transmission",
  "Media & Partnerships",
]

nav = [
  { label = "Approach",      href = "#approach" },
  { label = "Expertise",     href = "#services" },
  { label = "Selected Work", href = "#work" },
  { label = "Concepts",      href = "#concepts" },
  { label = "About",         href = "#about" },
  { label = "Contact",       href = "#contact" },
]

# ---- 01 approach ----------------------------------------------------

# The showreel. No video yet, so no player and no decorative play
# button — the client's own production note. `video` stays empty until
# a real file and a poster arrive.

# ---- 02 capabilities ------------------------------------------------

[[extra.services]]
name = "Creative Direction"
text = "Concept development, artistic vision, programming and experience design."

[[extra.services]]
name = "Live Performance & Artistic Direction"
text = "Performance concepts, artistic teams and creative supervision, in collaboration with production partners."

[[extra.services]]
name = "Culture, Sport & Learning"
text = "Participatory experiences, workshops and programmes that connect artistic practice, movement and transmission."

[[extra.services]]
name = "Partnership Development"
text = "Connecting relevant creative partners, venues, organisations and opportunities across sectors."

[[extra.services]]
name = "Original Formats"
text = "Developing adaptable concepts for different audiences, partners and locations."

[[extra.services]]
name = "Creative Collaboration"
text = "Joining existing projects as a creative director, artistic collaborator, curator or concept developer."

# ---- 03 selected work -----------------------------------------------
# ORDERED BY WIDENING DISCIPLINE, not by date: performance, then
# direction, then venue, then culture, then transmission, then
# international development. Chronology would need dates we do not have
# — one of the six is explicitly unverified — and a journey of maturity
# reads better than a CV besides.
#
# VERIFICATION IS A RECORD, NOT A FLAG.
#
# Brief V2 downgraded all six references to "à contrôler avant
# publication", so all six start unverified, and while any is unverified
# the site cannot go live — tools/content-check.py refuses it.
#
# `verified = true` alone is just somebody's word. So it is not enough:
# a verified entry must also carry WHEN it was checked and WHAT was
# checked against. The build rejects the flag without both, which means
# the honest answer to "how do we know this role is right?" is in the
# file rather than in someone's memory of a conversation.
#
#   verified    = true
#   verified_on = "2026-11-14"        the day it was confirmed
#   evidence    = "contract, 2023"    what was actually seen

[[extra.work]]
name = "Reference 01"
domain = "Performance × Premium Events"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
verified_on = ""
evidence = ""
image = "fragment-01.jpg"
alt = "Stand-in photograph — replaced at handover with the real case study"

[[extra.work]]
name = "Reference 02"
domain = "Sport × Culture"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
verified_on = ""
evidence = ""
image = "fragment-02.jpg"
alt = "Stand-in photograph — replaced at handover with the real case study"

[[extra.work]]
name = "Reference 03"
domain = "Artistic Direction × Venue"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
verified_on = ""
evidence = ""
image = "fragment-03.jpg"
alt = "Stand-in photograph — replaced at handover with the real case study"

[[extra.work]]
name = "Reference 04"
domain = "Culture × Experiences"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
verified_on = ""
evidence = ""
image = "fragment-04.jpg"
alt = "Stand-in photograph — replaced at handover with the real case study"

[[extra.work]]
name = "Reference 05"
domain = "Cinema × Education"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
verified_on = ""
evidence = ""

[[extra.work]]
name = "Reference 06"
domain = "Media × International"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
verified_on = ""
evidence = ""


# ---- the portfolio inside each reference -----------------------------
# A STAND-IN PORTFOLIO, so the gallery can be seen on the published page
# rather than only in a local fixture.
#
# Every photograph here is listed in content/PLACEHOLDERS.txt and goes
# with one command — `python3 tools/placeholders.py --purge` — which is
# the same bargain the four fragment images already make. They leave at
# handover not because of the licence, which allows this, but because a
# portfolio built from someone else's photographs misrepresents the
# artist whose name is on it. See NOTICE.
#
# Generated with the files, by tools/placeholders.py --blocks, so the
# page and the folder cannot disagree about what exists.

[[extra.project]]
id = "r1-a"
reference = 1
name = "Projet 1-A"

[[extra.project]]
id = "r1-b"
reference = 1
name = "Projet 1-B"

[[extra.project]]
id = "r1-c"
reference = 1
name = "Projet 1-C"

[[extra.project]]
id = "r1-d"
reference = 1
name = "Projet 1-D"

[[extra.project]]
id = "r1-e"
reference = 1
name = "Projet 1-E"

[[extra.project]]
id = "r2-a"
reference = 2
name = "Projet 2-A"

[[extra.project]]
id = "r2-b"
reference = 2
name = "Projet 2-B"

[[extra.project]]
id = "r2-c"
reference = 2
name = "Projet 2-C"

[[extra.project]]
id = "r2-d"
reference = 2
name = "Projet 2-D"

[[extra.project]]
id = "r3-a"
reference = 3
name = "Projet 3-A"

[[extra.project]]
id = "r3-b"
reference = 3
name = "Projet 3-B"

[[extra.project]]
id = "r3-c"
reference = 3
name = "Projet 3-C"

[[extra.project]]
id = "r3-d"
reference = 3
name = "Projet 3-D"

[[extra.project]]
id = "r3-e"
reference = 3
name = "Projet 3-E"

[[extra.project]]
id = "r4-a"
reference = 4
name = "Projet 4-A"

[[extra.project]]
id = "r4-b"
reference = 4
name = "Projet 4-B"

[[extra.project]]
id = "r4-c"
reference = 4
name = "Projet 4-C"

[[extra.project]]
id = "r4-d"
reference = 4
name = "Projet 4-D"

[[extra.project]]
id = "r5-a"
reference = 5
name = "Projet 5-A"

[[extra.project]]
id = "r5-b"
reference = 5
name = "Projet 5-B"

[[extra.project]]
id = "r5-c"
reference = 5
name = "Projet 5-C"

[[extra.project]]
id = "r5-d"
reference = 5
name = "Projet 5-D"

[[extra.project]]
id = "r5-e"
reference = 5
name = "Projet 5-E"

[[extra.project]]
id = "r6-a"
reference = 6
name = "Projet 6-A"

[[extra.project]]
id = "r6-b"
reference = 6
name = "Projet 6-B"

[[extra.project]]
id = "r6-c"
reference = 6
name = "Projet 6-C"

[[extra.project]]
id = "r6-d"
reference = 6
name = "Projet 6-D"

[[extra.photo]]
project = "r1-a"
file = "work-r1-a-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-a"
file = "work-r1-a-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-a"
file = "work-r1-a-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-a"
file = "work-r1-a-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-b"
file = "work-r1-b-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-b"
file = "work-r1-b-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-b"
file = "work-r1-b-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-c"
file = "work-r1-c-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-c"
file = "work-r1-c-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-c"
file = "work-r1-c-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-c"
file = "work-r1-c-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-c"
file = "work-r1-c-05.jpg"
alt = "Photographie 05 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-d"
file = "work-r1-d-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-d"
file = "work-r1-d-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-d"
file = "work-r1-d-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-d"
file = "work-r1-d-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-e"
file = "work-r1-e-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-e"
file = "work-r1-e-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r1-e"
file = "work-r1-e-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-a"
file = "work-r2-a-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-a"
file = "work-r2-a-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-a"
file = "work-r2-a-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-a"
file = "work-r2-a-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-b"
file = "work-r2-b-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-b"
file = "work-r2-b-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-b"
file = "work-r2-b-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-c"
file = "work-r2-c-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-c"
file = "work-r2-c-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-c"
file = "work-r2-c-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-c"
file = "work-r2-c-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-c"
file = "work-r2-c-05.jpg"
alt = "Photographie 05 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-d"
file = "work-r2-d-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-d"
file = "work-r2-d-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-d"
file = "work-r2-d-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r2-d"
file = "work-r2-d-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-a"
file = "work-r3-a-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-a"
file = "work-r3-a-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-a"
file = "work-r3-a-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-a"
file = "work-r3-a-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-b"
file = "work-r3-b-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-b"
file = "work-r3-b-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-b"
file = "work-r3-b-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-c"
file = "work-r3-c-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-c"
file = "work-r3-c-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-c"
file = "work-r3-c-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-c"
file = "work-r3-c-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-c"
file = "work-r3-c-05.jpg"
alt = "Photographie 05 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-d"
file = "work-r3-d-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-d"
file = "work-r3-d-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-d"
file = "work-r3-d-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-d"
file = "work-r3-d-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-e"
file = "work-r3-e-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-e"
file = "work-r3-e-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r3-e"
file = "work-r3-e-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-a"
file = "work-r4-a-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-a"
file = "work-r4-a-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-a"
file = "work-r4-a-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-a"
file = "work-r4-a-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-b"
file = "work-r4-b-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-b"
file = "work-r4-b-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-b"
file = "work-r4-b-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-c"
file = "work-r4-c-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-c"
file = "work-r4-c-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-c"
file = "work-r4-c-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-c"
file = "work-r4-c-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-c"
file = "work-r4-c-05.jpg"
alt = "Photographie 05 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-d"
file = "work-r4-d-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-d"
file = "work-r4-d-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-d"
file = "work-r4-d-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r4-d"
file = "work-r4-d-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-a"
file = "work-r5-a-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-a"
file = "work-r5-a-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-a"
file = "work-r5-a-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-a"
file = "work-r5-a-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-b"
file = "work-r5-b-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-b"
file = "work-r5-b-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-b"
file = "work-r5-b-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-c"
file = "work-r5-c-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-c"
file = "work-r5-c-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-c"
file = "work-r5-c-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-c"
file = "work-r5-c-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-c"
file = "work-r5-c-05.jpg"
alt = "Photographie 05 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-d"
file = "work-r5-d-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-d"
file = "work-r5-d-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-d"
file = "work-r5-d-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-d"
file = "work-r5-d-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-e"
file = "work-r5-e-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-e"
file = "work-r5-e-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r5-e"
file = "work-r5-e-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-a"
file = "work-r6-a-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-a"
file = "work-r6-a-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-a"
file = "work-r6-a-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-a"
file = "work-r6-a-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-b"
file = "work-r6-b-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-b"
file = "work-r6-b-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-b"
file = "work-r6-b-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-c"
file = "work-r6-c-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-c"
file = "work-r6-c-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-c"
file = "work-r6-c-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-c"
file = "work-r6-c-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-c"
file = "work-r6-c-05.jpg"
alt = "Photographie 05 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-d"
file = "work-r6-d-01.jpg"
alt = "Photographie 01 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-d"
file = "work-r6-d-02.jpg"
alt = "Photographie 02 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-d"
file = "work-r6-d-03.jpg"
alt = "Photographie 03 — image de remplacement, pas le travail du client"

[[extra.photo]]
project = "r6-d"
file = "work-r6-d-04.jpg"
alt = "Photographie 04 — image de remplacement, pas le travail du client"


# ---- 04 original concepts -------------------------------------------

[[extra.concepts]]
status = "In development"
name = "Format One"
text = "Concept name and description supplied at handover."

[[extra.concepts]]
status = "In development"
name = "Format Two"
text = "Concept name and description supplied at handover."

[[extra.concepts]]
status = "Opportunity area"
name = "Format Three"
text = "Concept name and description supplied at handover."

# ---- 05 professional ecosystem --------------------------------------

# ---- 06 about --------------------------------------------------------

[[extra.about_pillars]]
name = "Creative Direction & Performance"
text = "Dance, theatre, movement and live artistic projects"

[[extra.about_pillars]]
name = "Production Experience"
text = "Understanding teams, budgets, logistics and live delivery"

[[extra.about_pillars]]
name = "Pedagogy & Transmission"
text = "Learning programmes and cultural education"

[[extra.about_pillars]]
name = "Partnerships & Development"
text = "Cross-sector collaborations and international opportunities"

# ---- 07 contact ------------------------------------------------------
+++
