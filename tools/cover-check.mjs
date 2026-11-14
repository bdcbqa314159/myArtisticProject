/* The cover's floor, checked exactly.
 *
 *     node tools/cover-check.mjs
 *
 * This replaces a browser measurement that could not be trusted. The
 * old check timed the real cover from a parent page and asserted the
 * result fell between 380ms and 2000ms. It failed twice on a page that
 * was behaving perfectly — 41ms once, 5026ms another time — because a
 * virtual clock on a loaded machine cannot say how long something took.
 *
 * A check that fails at random is worse than no check: it gets
 * explained away, and then it gets ignored. So the duration is
 * arithmetic now and is answered here, and the browser is only asked
 * what it can answer reliably — did the cover appear, and did it leave.
 */
import assert from "node:assert/strict";
import { owedBeforeShowing } from "../static/js/cover.js";

const FLOOR = 450;          // must match COVER_FLOOR_MS in src/landing.ts
let checks = 0;
const is = (got, want, what) => { assert.equal(got, want, what); checks++; };

/* ---- the ordinary cases ---------------------------------------------- */
is(owedBeforeShowing(0, FLOOR), 450, "ready instantly: the whole floor is owed");
is(owedBeforeShowing(100, FLOOR), 350, "ready at 100ms: 350 left to wait");
is(owedBeforeShowing(449, FLOOR), 1, "ready a millisecond early: wait the one");

/* ---- the boundary, where a flicker would come from -------------------- */
is(owedBeforeShowing(450, FLOOR), 0, "ready exactly on the floor: nothing owed");
is(owedBeforeShowing(451, FLOOR), 0, "a millisecond late: nothing owed");
is(owedBeforeShowing(60_000, FLOOR), 0,
   "a slow page owes nothing — the floor is a minimum, never a delay added");

/* ---- and the clocks that misbehave ------------------------------------
 * `performance.now()` is well behaved in a browser. It is not well
 * behaved in every environment this code has been run in: the headless
 * harness drives a virtual clock, and a probe that pauses an animation
 * and sets its time by hand can hand it anything at all. A negative
 * wait passed to setTimeout fires immediately, which would reintroduce
 * the flicker this floor exists to prevent. */
is(owedBeforeShowing(-5, FLOOR), 450, "a clock that went backwards owes the floor");
is(owedBeforeShowing(Number.NaN, FLOOR), 450, "a clock that is not a number");
/* Infinity reads as "ages have passed", which would argue for 0. It is
 * not a reading any clock gives, though, and the two wrong answers are
 * not equal: waiting 450ms when nothing was owed costs nothing anyone
 * notices, and revealing instantly when the floor WAS owed is the
 * flicker the floor exists to prevent. An unusable clock waits. */
is(owedBeforeShowing(Number.POSITIVE_INFINITY, FLOOR), 450,
   "a clock past everything is not a clock — wait the floor");
is(owedBeforeShowing(10, 0), 0, "no floor configured: nothing is owed");
is(owedBeforeShowing(10, -1), 0, "a negative floor is not a wait");

/* The one thing that must never happen: a negative delay. */
for (const since of [0, 1, 449, 450, 451, 99_999, -1, Number.NaN]) {
  assert.ok(owedBeforeShowing(since, FLOOR) >= 0,
            `a negative wait from since=${since}`);
  checks++;
}

console.log(`\n  cover: the floor holds at ${checks} points, including the `
  + `clocks that misbehave\n`);
