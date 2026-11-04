/* The one check behind src/drift.ts.
 *
 *     node tools/drift-check.mjs
 *
 * The drift itself cannot be checked in CI: it needs a browser that
 * scrolls and runs animation frames, and the headless one does neither.
 * The arithmetic can be, and this is it.
 */
import assert from "node:assert/strict";
import { shiftFor } from "../static/js/drift.js";

const V = 900;      // viewport
const H = 300;      // photograph
const A = 14;       // amount

// Centred in the viewport: still. This is the one that matters — a
// photograph should be where it belongs when you are looking at it.
assert.equal(shiftFor(V / 2 - H / 2, H, V, A), 0);

// Entering from the bottom: pushed down. Leaving at the top: pulled up.
assert.ok(shiftFor(V - 10, H, V, A) < 0, "entering from below moves up-screen");
assert.ok(shiftFor(-H + 10, H, V, A) > 0, "leaving at the top moves down-screen");

// Symmetric about the centre.
const above = shiftFor(V / 2 - H / 2 - 200, H, V, A);
const below = shiftFor(V / 2 - H / 2 + 200, H, V, A);
assert.ok(Math.abs(above + below) < 1e-9, "equal distances either side give equal shifts");

// Never more than the amount, however far away — otherwise a photograph
// arrives from somewhere it was never drawn.
for (const top of [-10000, -1000, 0, 450, 1000, 10000]) {
  const s = shiftFor(top, H, V, A);
  assert.ok(Math.abs(s) <= A + 1e-9, `|${s}| exceeds ${A} at top=${top}`);
}

// A viewport of nothing is not a division by zero.
assert.equal(shiftFor(0, H, 0, A), 0);

console.log("  drift: the arithmetic holds at 11 positions");
