/* The one check behind src/scroll.ts.
 *
 *     node tools/scroll-check.mjs
 */
import assert from "node:assert/strict";
import { ease, scrollDuration } from "../static/js/scroll.js";

// Never shorter than the floor, never longer than the ceiling, however
// far the page is asked to travel.
for (const d of [0, 1, 400, 2000, 50_000, -3000]) {
  const ms = scrollDuration(d);
  assert.ok(ms >= 480 && ms <= 1100, `${ms}ms for ${d}px is outside the clamp`);
}

// Longer journeys take longer, up to the ceiling.
assert.ok(scrollDuration(2000) > scrollDuration(200), "further should take longer");
assert.equal(scrollDuration(0), 480, "no distance is still the floor, not zero");

// A distance that is not a number means something upstream is broken.
// The answer is the SHORTEST animation, not the longest: get the reader
// where they asked to go and stop, rather than crawl for a second
// because a measurement failed.
assert.equal(scrollDuration(Number.NaN), 480);
assert.equal(scrollDuration(Number.POSITIVE_INFINITY), 480);

// The easing starts and ends where it must, and is symmetric.
assert.equal(ease(0), 0);
assert.equal(ease(1), 1);
assert.ok(Math.abs(ease(0.5) - 0.5) < 1e-9, "half way through is half way there");
assert.ok(Math.abs(ease(0.25) + ease(0.75) - 1) < 1e-9, "symmetric about the middle");
// Out of range is clamped rather than extrapolated past the target.
assert.equal(ease(-1), 0);
assert.equal(ease(2), 1);

console.log("  scroll: duration clamped and easing sound at 12 points");
