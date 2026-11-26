/* Asking again for an image that did not arrive.
 *
 *     node tools/lost-check.mjs
 *
 * `src/lost.ts` decides how many times a failed image is asked for
 * again, how long it waits between asks, and when it gives up and lets
 * the box go quiet. None of that can be driven in a browser here — the
 * failure has to be real and the waits are seconds long — so the clock
 * and the page are arguments, and this file supplies both.
 *
 * What is being protected:
 *
 *   - a dropped image is asked for again, because the landing that
 *     dropped it is a crowd that clears;
 *   - it is not asked for ever: a file that is not there must not be
 *     hammered from a phone by a page the reader has already scrolled
 *     past;
 *   - the second wait is longer than the first;
 *   - an image that arrives forgets its failures, so a LATER failure
 *     gets its own two tries rather than inheriting a spent budget;
 *   - and when it is given up on, the page is told every time, because
 *     that is what puts the quiet pixel in the box and an image failing
 *     over and over must not go quiet in the console as well.
 */
import assert from "node:assert/strict";
import { recovering } from "../static/js/lost.js";

let checks = 0;
const is = (got, want, what) => { assert.deepEqual(got, want, what); checks++; };
const ok = (cond, what) => { assert.ok(cond, what); checks++; };

/** A page that writes down what it was asked to do. */
function page() {
  const asked = [];
  const gone = [];
  return {
    asked,
    gone,
    retry: (key, wait) => asked.push(`${key}@${wait}`),
    giveUp: (key) => gone.push(key),
  };
}

/* ---- the ordinary case: dropped in the crowd, then it arrives ------- */
{
  const p = page();
  const r = recovering(p);

  ok(r.failed("a.webp"), "a dropped image is asked for again");
  is(p.asked, ["a.webp@900"], "after a wait, not at once — the crowd that "
     + "dropped it is still there");
  is(p.gone, [], "nothing has been given up on");

  r.arrived("a.webp");
  is(r.tries("a.webp"), 0, "an image that arrives forgets what went before");
}

/* ---- twice, and then it is let go ----------------------------------- */
{
  const p = page();
  const r = recovering(p);

  ok(r.failed("b.webp"), "once");
  ok(r.failed("b.webp"), "twice");
  is(p.asked, ["b.webp@900", "b.webp@1800"],
     "the second wait is longer: a crowd that has not cleared in 900ms is "
     + "unlikely to have cleared by then either");

  is(r.failed("b.webp"), false, "the third failure is not asked for again");
  is(p.gone, ["b.webp"], "it is given up on, which is what puts the quiet "
     + "pixel in the box");
  is(p.asked.length, 2, "and no third ask was made");
}

/* ---- told exactly once ---------------------------------------------- */
{
  const p = page();
  const r = recovering(p);
  r.failed("c.webp"); r.failed("c.webp"); r.failed("c.webp");
  r.failed("c.webp"); r.failed("c.webp");
  is(p.gone.filter((k) => k === "c.webp").length, 3,
     "five failures: the first two are asked again, and every one past the "
     + "budget reports again — the page makes that idempotent by setting a "
     + "class, and a counter that went quiet would hide an image failing "
     + "over and over");
  is(p.asked.length, 2, "but it is never ASKED for again");
}

/* ---- a second failure, long after it arrived ------------------------- */
{
  const p = page();
  const r = recovering(p);
  r.failed("d.webp");
  r.arrived("d.webp");
  ok(r.failed("d.webp"), "it failed again later — a swap to the bigger copy, "
     + "say — and gets its own budget");
  is(p.asked, ["d.webp@900", "d.webp@900"],
     "from the beginning, not from where the last failure left off");
}

/* ---- each image has its own budget ----------------------------------- */
{
  const p = page();
  const r = recovering(p);
  r.failed("e.webp"); r.failed("e.webp"); r.failed("e.webp");
  ok(r.failed("f.webp"), "one image running out does not spend another's");
  is(p.gone, ["e.webp"], "and only the one that ran out is given up on");
}

/* ---- a shorter rope, where the caller wants one -------------------- */
{
  const p = page();
  const r = recovering(p, 1, 200);
  ok(r.failed("g.webp"), "one try");
  is(r.failed("g.webp"), false, "and that is the lot");
  is(p.asked, ["g.webp@200"], "with the wait the caller chose");
}

console.log(`\n  lost: a dropped image is asked for again, twice, and then `
  + `let go quietly, at ${checks} points\n`);
