/* One horizon, checked at the two shapes of screen that matter.
 *
 *     node tools/horizon-check.mjs
 *
 * A project's photographs should be the same size as each other. On a
 * wide screen they already were — the slide is short and wide, so the
 * height binds all of them — and on a phone they were not: the width
 * binds instead, so an upright photograph came out twice the height of
 * a landscape one.
 *
 * `horizonFor` picks the height they can all share: the tallest at
 * which the WIDEST of them still fits. Arithmetic, and the cases that
 * matter are the awkward ones, so they are here rather than in a
 * browser that cannot be resized.
 */
import assert from "node:assert/strict";
import { horizonFor } from "../static/js/horizon.js";

let checks = 0;
const near = (got, want, what) => {
  assert.ok(Math.abs(got - want) < 1, `${what} — got ${got}, wanted ${want}`);
  checks++;
};

const LANDSCAPE = 1000 / 667;      // 1.4993, the common case
const UPRIGHT = 750 / 1000;        // 0.75
const PANORAMA = 3;

/* ---- a phone: 390 wide, a slide 621 tall ----------------------------- */
near(horizonFor([LANDSCAPE, UPRIGHT], 390, 621), 260,
     "the landscape photograph fills the width at 260px tall, and the "
     + "upright one comes down to meet it");
near(horizonFor([UPRIGHT, UPRIGHT], 390, 621), 520,
     "all upright: the horizon is theirs, not a landscape's");
near(horizonFor([LANDSCAPE, LANDSCAPE], 390, 621), 260, "all landscape");

/* ---- a desktop: 1400 wide, a slide 801 tall -------------------------- */
near(horizonFor([LANDSCAPE, UPRIGHT], 1400, 801), 801,
     "on a wide screen the slide's own height still binds — which is why "
     + "they already looked uniform there, and why this changes nothing");

/* ---- one very wide photograph decides for everyone ------------------- */
near(horizonFor([LANDSCAPE, UPRIGHT, PANORAMA], 390, 621), 130,
     "a panorama in the set brings the horizon down to where IT fits: "
     + "nothing is cropped, so the widest photograph decides");

/* ---- a project with one photograph ----------------------------------- */
near(horizonFor([UPRIGHT], 390, 621), 520, "one upright photograph");
near(horizonFor([LANDSCAPE], 1400, 801), 801,
     "one landscape on a desktop: the slide binds");

/* ---- and never taller than the photograph's own pixels --------------- */
near(horizonFor([LANDSCAPE, UPRIGHT], 1400, 801, 667), 667,
     "the slide is 801 tall and the shortest photograph has 667 pixels: "
     + "forcing the common height to the slide would stretch that one, "
     + "which is the thing none of this is allowed to do");
near(horizonFor([LANDSCAPE, UPRIGHT], 1400, 801, 1333), 801,
     "with real photography — 2000px on the long edge — the ceiling is "
     + "above the slide and binds nothing");
near(horizonFor([LANDSCAPE], 390, 621, 667), 260,
     "on a phone the width binds long before the pixels do");

/* ---- nothing to measure ----------------------------------------------- */
near(horizonFor([], 390, 621), 621,
     "no aspects yet — before anything has loaded — is the slide's own "
     + "height, which is what it was doing before");
near(horizonFor([0, NaN, -2], 390, 621), 621, "and nonsense is not an aspect");
near(horizonFor([LANDSCAPE], 0, 621), 621, "a slide of no width yet");

console.log(`\n  horizon: a project's photographs share a height, at ${checks} points\n`);
