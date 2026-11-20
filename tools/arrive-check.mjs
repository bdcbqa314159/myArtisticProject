/* Arriving twice plays twice.
 *
 *     node tools/arrive-check.mjs
 *
 * The page's two reveals — the blocks that fade and rise, and the
 * headlines released word by word — used to fire once and unobserve.
 * They now play on every arrival, which is what the client asked for
 * after watching it: "I keep scrolling down and now imagine I get back
 * again to it — the title stays in place and no animation."
 *
 * WHY THIS IS A NODE CHECK AND NOT A BROWSER ONE.
 *
 * An IntersectionObserver callback is delivered on a rendering
 * opportunity. `tools/render-check.py` drives the page inside an
 * iframe, which in this browser gets none — measured by scrolling four
 * thousand pixels down and back up and reading the classes: 0 of 28
 * blocks marked, before and after, with no code to blame. So the
 * reveals cannot be observed there at all, and a check that cannot
 * fail is worse than no check.
 *
 * What CAN be checked exactly is the wiring, which is where the bug
 * was: one observer instead of two, the wrong margin on the reset, or
 * an unobserve creeping back. `src/arrive.ts` takes the observer as an
 * argument for that reason; this passes a fake one.
 */
import assert from "node:assert/strict";
import { whileInView } from "../static/js/arrive.js";

let checks = 0;
const is = (got, want, what) => { assert.deepEqual(got, want, what); checks++; };
const ok = (cond, what) => { assert.ok(cond, what); checks++; };

/** A fake observer that records everything it was asked to do. */
function fake() {
  const made = [];
  const make = (callback, options) => {
    const watcher = { options, observed: [], callback,
                      observe(el) { this.observed.push(el); } };
    made.push(watcher);
    return watcher;
  };
  return { made, make };
}

const el = (name) => ({ name });
const marks = [];
const mark = (target, on) => marks.push([target.name, on]);

/* ---- the wiring ------------------------------------------------------ */
{
  const { made, make } = fake();
  whileInView([el("a"), el("b")], make, mark);

  is(made.length, 2, "two observers: one for arriving, one for leaving");
  ok(made[0].options.rootMargin === "0px 0px -12% 0px",
     "arriving fires early, 12% before the block's top edge lands");
  ok(made[0].options.threshold === 0.01,
     "and on the first sliver of it, not a tenth");

  /* THE ONE THAT MATTERS. With the arriving margin on the reset, a
   * block scrolled back towards from below stops intersecting while it
   * is still on screen — and the words retract in front of the reader. */
  ok(!made[1].options.rootMargin || made[1].options.rootMargin === "0px",
     "leaving watches the viewport EXACTLY. A margin here resets a block "
     + "that is still visible, in front of the reader");
  is(made[1].options.threshold, 0, "and resets only when entirely out of sight");

  is(made[0].observed.map((e) => e.name), ["a", "b"], "every block is watched for arriving");
  is(made[1].observed.map((e) => e.name), ["a", "b"], "every block is watched for leaving");

  /* Nothing stops watching. The type has no `unobserve` at all, which
   * is the point — but a fake records what it was asked for, and this
   * says plainly that nothing else was. */
  for (const watcher of made) {
    ok(Object.keys(watcher).every((k) =>
         ["options", "observed", "callback", "observe"].includes(k)),
       "an observer was asked for something other than observe()");
  }
}

/* ---- what the callbacks do ------------------------------------------- */
{
  const { made, make } = fake();
  marks.length = 0;
  whileInView([el("one")], make, mark);
  const [arriving, leaving] = made;
  const a = el("one");

  arriving.callback([{ target: a, isIntersecting: true }]);
  is(marks, [["one", true]], "arriving marks the block");

  marks.length = 0;
  arriving.callback([{ target: a, isIntersecting: false }]);
  is(marks, [], "the arriving observer never unmarks — that is the other one's "
     + "job, and doing it here would use the early margin");

  marks.length = 0;
  leaving.callback([{ target: a, isIntersecting: false }]);
  is(marks, [["one", false]], "leaving unmarks it");

  marks.length = 0;
  leaving.callback([{ target: a, isIntersecting: true }]);
  is(marks, [], "and the leaving observer never marks");

  /* The whole point, as a sequence: in, out, in again. */
  marks.length = 0;
  arriving.callback([{ target: a, isIntersecting: true }]);
  leaving.callback([{ target: a, isIntersecting: false }]);
  arriving.callback([{ target: a, isIntersecting: true }]);
  is(marks, [["one", true], ["one", false], ["one", true]],
     "arriving a second time does not mark it again — which is the bug "
     + "being fixed: the reveal played once and never after");
}

/* ---- the headlines pass their own numbers --------------------------- */
{
  const { made, make } = fake();
  whileInView([el("h2")], make, mark, "0px", 0.1);
  ok(made[0].options.rootMargin === "0px",
     "a headline waits until it is actually on screen");
  is(made[0].options.threshold, 0.1, "a tenth of it in view");
  is(made[1].options.threshold, 0, "and the reset is unchanged by that");
}

/* ---- nothing to watch is not an error ------------------------------- */
{
  const { made, make } = fake();
  whileInView([], make, mark);
  is(made.length, 2, "observers are made even with nothing to watch");
  is(made[0].observed, [], "and nothing is observed");
}

console.log(`\n  arrive: a reveal plays on every arrival, at ${checks} points\n`);
