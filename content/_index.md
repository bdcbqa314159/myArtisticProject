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
work_lead = "Selected organisations and professional roles from the artist's career. Individual case studies can be expanded with verified media, dates, credits and deliverables."
work_note = "Professional references above do not imply that each organisation is a contracted partner."
concepts_title = "Formats in development."
concepts_lead = "Original ideas designed to evolve through partnerships and pilot projects. These are development concepts, not completed client commissions."
ecosystem_title = "Independent by design. Collaborative by nature."
ecosystem_lead = "10MILES draws on cross-sector experience and a professional network spanning artistic creation, performance, sport, cultural venues, education and media. Creative collaborations are shaped around each project, with production handled by appropriate partners."
about_title = "Built on practice. Open to new territories."
about_text = "Experience in artistic and operational roles helps connect creative ambition with the realities of delivery. Through 10MILES, the artist develops concepts and international collaborations, with a priority market abroad."
contact_title = "Let's build something together."
contact_lead = "For creative direction, experience design, original concepts and collaborations."
contact_pending = "Email contact — to configure"
contact_copy = "Copy introduction"
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
# `verified = false` means the role has not been checked against the
# record yet. Brief V2 downgraded ALL SIX to "à contrôler avant
# publication", so all six start false. While any is false the site
# cannot go live: tools/content-check.py refuses it. Flip each one as it
# is confirmed, and the gate opens by itself.

[[extra.work]]
name = "Reference 01"
domain = "Performance × Premium Events"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
image = "fragment-01.jpg"

[[extra.work]]
name = "Reference 02"
domain = "Sport × Culture"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
image = "fragment-02.jpg"

[[extra.work]]
name = "Reference 03"
domain = "Artistic Direction × Venue"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
image = "fragment-03.jpg"

[[extra.work]]
name = "Reference 04"
domain = "Culture × Experiences"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false
image = "fragment-04.jpg"

[[extra.work]]
name = "Reference 05"
domain = "Cinema × Education"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false

[[extra.work]]
name = "Reference 06"
domain = "Media × International"
text = "Description supplied at handover."
role = "Role supplied at handover, once verified."
verified = false


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
