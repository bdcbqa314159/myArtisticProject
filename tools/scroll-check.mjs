/* The one check behind src/scroll.ts.
 *
 *     node tools/scroll-check.mjs
 */
import assert from "node:assert/strict";
import { animateScroll, ease, scrollDuration } from "../static/js/scroll.js";

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


/* ---- the journey, driven by a fake clock -------------------------------
 *
 * This is why the loop lives in scroll.ts. The headless browser used for
 * the render checks runs no animation frames — measured, with and
 * without virtual time — so in a browser this could only be argued for.
 * Here the clock and the frames are ours, and the argument is a test.
 *
 * The guarantee under examination: a journey reports its end EXACTLY
 * ONCE, however it ends. The navigation band holds its underline still
 * until that call arrives, so a call that never comes leaves the band
 * frozen on the wrong section, and a call that comes twice is a release
 * that outlives the journey that earned it.
 */
function rig({ from = 0 } = {}) {
  let t = 0;
  let y = from;
  const pending = new Map();
  let next = 1;
  let interrupt = null;
  let listening = false;
  const settled = [];

  const env = {
    now: () => t,
    position: () => y,
    moveTo: (v) => { y = v; },
    frame: (cb) => { pending.set(next, cb); return next++; },
    cancelFrame: (h) => { pending.delete(h); },
    whenInterrupted(give) {
      interrupt = give;
      listening = true;
      return () => { listening = false; };
    },
  };

  return {
    env,
    settled,
    get y() { return y; },
    get listening() { return listening; },
    onSettled: () => settled.push(t),
    /** Run the frames that are due, advancing the clock by `ms` each. */
    tick(ms = 16, times = 1) {
      for (let i = 0; i < times; i++) {
        t += ms;
        const due = [...pending.entries()];
        pending.clear();
        for (const [, cb] of due) cb(t);
      }
    },
    /** The reader takes over. */
    interrupt() { interrupt?.(); },
  };
}

// 1. A completed journey lands exactly on the target and settles once.
{
  const r = rig();
  animateScroll(r.env, 1000, r.onSettled);
  r.tick(16, 200);
  assert.equal(r.y, 1000, "a finished scroll ends exactly on the target");
  assert.equal(r.settled.length, 1, "arriving settles exactly once");
  assert.equal(r.listening, false, "and takes its listeners off again");
}

// 2. It never overshoots, and only ever moves towards the target.
{
  const r = rig();
  const seen = [];
  const env = { ...r.env, moveTo: (v) => { seen.push(v); r.env.moveTo(v); } };
  animateScroll(env, 800, r.onSettled);
  r.tick(16, 200);
  assert.ok(Math.max(...seen) <= 800 + 1e-9, "never travels past the target");
  assert.ok(Math.min(...seen) >= 0 - 1e-9, "never travels backwards past the start");
  for (let i = 1; i < seen.length; i++) {
    assert.ok(seen[i] >= seen[i - 1], "the page only ever moves forwards");
  }
}

// 3. The reader taking over settles it once, and stops the movement.
{
  const r = rig();
  animateScroll(r.env, 5000, r.onSettled);
  r.tick(16, 3);
  const stoppedAt = r.y;
  r.interrupt();
  r.tick(16, 50);
  assert.equal(r.settled.length, 1, "being interrupted settles exactly once");
  assert.equal(r.y, stoppedAt, "and the page stays where the reader left it");
  assert.equal(r.listening, false);
}

// 4. THE DOUBLE CALL. Abandoning runs finish(), and the frame already in
//    flight then runs it again — this is the case the guard exists for,
//    and the one that would have shipped without a test.
{
  const r = rig();
  const abandon = animateScroll(r.env, 5000, r.onSettled);
  r.tick(16, 2);
  abandon();                       // finish() once, from here
  r.tick(16, 5);                   // the in-flight frame finds `cancelled`
  assert.equal(r.settled.length, 1, "abandoning mid-flight settles exactly once");
  abandon();
  abandon();
  assert.equal(r.settled.length, 1, "abandoning again changes nothing");
}

// 4b. Abandoning settles IMMEDIATELY, not on the next frame.
//
//     Found by mutation: a version where `abandon()` only set the flag
//     and left `finish()` to the frame already in flight passed every
//     test above, because the ending still arrived — one frame late.
//
//     One frame is the difference between a correct page and a wrong
//     one. `scrollTo` abandons the old journey as the new one starts,
//     so a late ending lands AFTER the new click has locked the band,
//     and releases a lock it does not own.
{
  const r = rig();
  const abandon = animateScroll(r.env, 5000, r.onSettled);
  r.tick(16, 2);
  abandon();
  assert.equal(
    r.settled.length, 1,
    "abandoning must settle before control returns, not on the next frame",
  );
}

// 5. A journey of no distance still settles — otherwise a click on the
//    section you are already in would leave the band locked for ever.
{
  const r = rig({ from: 400 });
  animateScroll(r.env, 400, r.onSettled);
  r.tick(16, 200);
  assert.equal(r.settled.length, 1, "a zero-distance journey still reports its end");
  assert.equal(r.y, 400);
}

// 6. Upwards works the same way.
{
  const r = rig({ from: 3000 });
  animateScroll(r.env, 500, r.onSettled);
  r.tick(16, 200);
  assert.equal(r.y, 500, "travelling up lands on the target too");
  assert.equal(r.settled.length, 1);
}

// 7. onSettled is optional — the loop must not require one.
{
  const r = rig();
  assert.doesNotThrow(() => { animateScroll(r.env, 100); r.tick(16, 200); });
}

// 8. The marker is held for the WHOLE journey. This is the bug: the band
//    used to be released by a 900ms timer while the scroll ran to 1100ms,
//    so every long jump unlocked mid-flight. Settling is now the signal,
//    so by construction it cannot be early — assert it directly.
{
  const r = rig();
  animateScroll(r.env, 9000, r.onSettled);
  let frames = 0;
  while (r.settled.length === 0 && frames < 1000) { r.tick(16); frames++; }
  assert.equal(r.settled.length, 1);
  assert.ok(
    r.settled[0] >= scrollDuration(9000),
    `settled at ${r.settled[0]}ms, before the ${scrollDuration(9000)}ms journey ended`,
  );
  assert.equal(r.y, 9000, "and the page actually got there");
}

console.log("  scroll: duration and easing sound at 12 points; the journey settles exactly once by all 4 roads out");
