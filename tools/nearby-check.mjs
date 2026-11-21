/* What the reader is about to reach, checked exactly.
 *
 *     node tools/nearby-check.mjs
 *
 * The warming queue used to work through the page in the order it is
 * written. That is right for someone reading from the top and wrong
 * for everybody else: jump to Concepts from the menu and the queue is
 * still fetching the references above it, so the photographs arrive
 * while they are being looked at.
 *
 * `src/nearby.ts` decides what is near. It is arithmetic, and the
 * cases that matter are the awkward ones — above the viewport,
 * straddling it, exactly on the edge of reach, not yet laid out — so
 * it is checked here rather than in a browser that cannot be scrolled.
 */
import assert from "node:assert/strict";
import { within } from "../static/js/nearby.js";

let checks = 0;
const is = (got, want, what) => { assert.deepEqual(got, want, what); checks++; };

const at = (url, top, height = 200) => ({ url, top, height });
const PAGE = [
  at("hero", 0, 600),
  at("approach", 900),
  at("work", 2000),
  at("concepts", 4000),
  at("about", 6000),
  at("footer", 9000),
];
const SCREEN = 800;

/* ---- reading from the top -------------------------------------------- */
is(within(PAGE, 0, SCREEN), ["hero", "approach"],
   "at the top: what is on screen and what is within two screens of it, "
   + "nearest first — and nothing from two thousand pixels down");

/* ---- and jumping into the middle ------------------------------------- */
is(within(PAGE, 4000, SCREEN), ["concepts"],
   "jumped to Concepts: that section, not the references above it. That "
   + "is the whole point — the queue used to work through the page in "
   + "the order it is written");

/* ---- a page where the photographs are close together ------------------ */
{
  /* The real one. A reference's card, its patchwork and its strip are
   * within a screen of each other, so the reach covers several. */
  const dense = [
    at("r1", 1800), at("r2", 2100), at("r3", 2400),
    at("r4", 2700), at("r5", 3000), at("r6", 5200),
  ];
  is(within(dense, 2300, SCREEN), ["r3", "r2", "r4", "r1", "r5"],
     "nearest first, outwards from where the reader is — and the one "
     + "two thousand pixels further down waits");
}

/* ---- the edges of reach ---------------------------------------------- */
{
  const edge = [at("just-in", 1600), at("just-out", 1601)];
  is(within(edge, 0, SCREEN, 2), ["just-in"],
     "two screens is the reach, and 1601 is past it");
  is(within(edge, 0, SCREEN, 3), ["just-in", "just-out"],
     "and a longer reach takes both");
}

/* ---- a tall box that straddles the viewport --------------------------- */
is(within([at("tall", -2000, 5000)], 0, SCREEN), ["tall"],
   "a photograph taller than the screen, starting above it, is on screen "
   + "and must be fetched");

/* ---- not laid out yet ------------------------------------------------- */
is(within([at("unmeasured", 400, 0)], 0, SCREEN), ["unmeasured"],
   "a box of no height is kept: an image that has not been laid out "
   + "reports nothing, and it is usually the one about to matter");

/* ---- nothing with a url ------------------------------------------------ */
is(within([at("", 100), at("real", 120)], 0, SCREEN), ["real"],
   "an image with no source is not something to fetch");

/* ---- order is by distance, not by document position ------------------- */
is(within([at("far-below", 1200), at("just-above", -100)], 300, SCREEN),
   ["just-above", "far-below"],
   "nearest first, whichever side of the reader it is on");

/* ---- an empty page ----------------------------------------------------- */
is(within([], 0, SCREEN), [], "nothing to warm is not an error");

console.log(`\n  nearby: the queue follows the reader, at ${checks} points\n`);
