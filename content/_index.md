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
cta_contact = "Start a conversation"

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
ecosystem_title = "Independent by design. Collaborative by nature."
ecosystem_lead = "I draw on cross-sector experience and a professional network spanning artistic creation, performance, sport, cultural venues, education and media. I shape creative collaborations around each project, with production handled by the right partners."
about_title = "Built on practice. Open to new territories."
about_text = "Working across artistic and operational roles helps me connect creative ambition with the realities of delivery. Through 10MILES I develop concepts and international collaborations, with a priority market abroad."
contact_title = "Let's build something together."
contact_lead = "For creative direction, experience design, original concepts and collaborations."
contact_pending = "Email contact — to configure"
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
