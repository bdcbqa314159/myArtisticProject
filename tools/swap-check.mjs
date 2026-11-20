/* The exchange plays on every arrival, and survives being interrupted.
 *
 *     node tools/swap-check.mjs
 *
 * "Independent by design. Collaborative by nature." — the one animated
 * heading that did not replay. The brief said once per appearance, with
 * no loop; it was built as once per page.
 *
 * The sequence has a timer in it, and the case that can break it
 * silently is a reader who leaves MID-FLIGHT: if the settle timer is
 * left running it fires while the section is gone, strips the offset,
 * and the next arrival finds the phrases already in place and plays
 * nothing at all — the exact bug being fixed, back again, with every
 * other check still green.
 *
 * It cannot be driven in a browser here: the trigger is an
 * IntersectionObserver, whose callbacks need a rendering opportunity,
 * and this repository drives the page inside an iframe, which gets
 * none. So `src/swap.ts` takes the page as an argument and this passes
 * a fake one — the same arrangement as `tools/arrive-check.mjs`.
 */
import assert from "node:assert/strict";
import { swapOnArrival } from "../static/js/swap.js";

const SETTLE = 1500;
let checks = 0;
const is = (got, want, what) => { assert.deepEqual(got, want, what); checks++; };
const ok = (cond, what) => { assert.ok(cond, what); checks++; };

/** A stage that writes down what it was asked to do, and a clock that
 *  only moves when this file says so. */
function stage() {
  const did = [];
  let next = 1;
  const timers = new Map();
  return {
    did,
    timers,
    tick(ms) {
      for (const [handle, timer] of [...timers]) {
        if (timer.at <= ms) { timers.delete(handle); timer.run(); }
      }
    },
    park: () => did.push("park"),
    play: () => did.push("play"),
    stop: () => did.push("stop"),
    rest: () => did.push("rest"),
    after(ms, run) {
      const handle = next++;
      timers.set(handle, { at: ms, run });
      did.push(`after:${ms}`);
      return handle;
    },
    cancel(handle) { if (timers.delete(handle)) did.push("cancel"); },
  };
}

/* ---- arriving -------------------------------------------------------- */
{
  const s = stage();
  const arrived = swapOnArrival(s, SETTLE);

  arrived(true);
  is(s.did, ["park", "play", `after:${SETTLE}`],
     "arriving parks the phrases, starts the animation, and sets the settle "
     + "— parked BEFORE playing, or the animation's first frame is not where "
     + "the phrases are and the heading jumps");

  s.did.length = 0;
  s.tick(SETTLE);
  is(s.did, ["rest", "stop"],
     "once spent, the offset goes and the animation comes off — in that "
     + "order, so there is no frame with the animation gone and the offset "
     + "still on");
}

/* ---- and arriving again ---------------------------------------------- */
{
  const s = stage();
  const arrived = swapOnArrival(s, SETTLE);

  arrived(true);
  s.tick(SETTLE);
  arrived(false);          // scrolled away, entirely out of sight
  s.did.length = 0;
  arrived(true);           // and back
  ok(s.did.includes("park") && s.did.includes("play"),
     "arriving a second time plays it again — the whole point");
}

/* ---- leaving while it is still playing ------------------------------- */
{
  const s = stage();
  const arrived = swapOnArrival(s, SETTLE);

  arrived(true);
  s.did.length = 0;
  arrived(false);                       // gone, mid-animation
  is(s.did, ["cancel", "stop", "park"],
     "leaving mid-flight cancels the settle, takes the animation off, and "
     + "parks them again");
  is(s.timers.size, 0,
     "the settle timer is really gone. Left running it fires while the "
     + "section is off screen, strips the offset, and the next arrival "
     + "plays nothing");

  s.did.length = 0;
  s.tick(SETTLE * 10);
  is(s.did, [], "and nothing happens later on its own");

  s.did.length = 0;
  arrived(true);
  ok(s.did.includes("play"), "the next arrival still plays");
}

/* ---- leaving when it was never playing ------------------------------- */
{
  const s = stage();
  const arrived = swapOnArrival(s, SETTLE);
  arrived(false);
  is(s.did, ["stop", "park"],
     "a leave with nothing in flight is still safe: parked, not left bare");
}

/* ---- two arrivals in a row, with no leave between -------------------- */
{
  const s = stage();
  const arrived = swapOnArrival(s, SETTLE);
  arrived(true);
  s.did.length = 0;
  arrived(true);
  is(s.did.filter((d) => d === "cancel").length, 1,
     "a second arrival cancels the first one's settle rather than letting "
     + "two timers strip the offset out from under the animation");
  is(s.timers.size, 1, "and leaves exactly one pending");
}

console.log(`\n  swap: the exchange plays on every arrival and survives being `
  + `interrupted, at ${checks} points\n`);
