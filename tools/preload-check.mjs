/* The warming queue, driven by hand.
 *
 *     node tools/preload-check.mjs
 *
 * `src/preload.ts` decides the order photographs are fetched in, how
 * many at once, and what happens when one fails. None of that can be
 * driven in a browser here — the harness runs the page in an iframe
 * with no rendering opportunities, and the queue is paced by idle
 * callbacks — so the fetcher and the idle scheduler are arguments, and
 * this file supplies fakes with a clock it controls.
 *
 * What is being protected:
 *
 *   - the reader's own request jumps the queue, however long the queue
 *     is: the whole point of the tiers;
 *   - never more than `width` fetches at once, or the warming competes
 *     with the page it is warming;
 *   - nothing is fetched twice, however many times it is asked for;
 *   - one failure does not stop the queue — 150 photographs, and the
 *     one that 404s must not take the other 149 with it.
 */
import assert from "node:assert/strict";
import { warming, worthWarmingBigCopies } from "../static/js/preload.js";

let checks = 0;
const is = (got, want, what) => { assert.deepEqual(got, want, what); checks++; };
const ok = (cond, what) => { assert.ok(cond, what); checks++; };

/** A fetcher that only resolves when this file says so. */
function hand() {
  const asked = [];
  const open = new Map();
  return {
    asked,
    fetch(url) {
      asked.push(url);
      return new Promise((resolve, reject) => open.set(url, { resolve, reject }));
    },
    async done(url) {
      open.get(url).resolve();
      open.delete(url);
      await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    },
    async failed(url) {
      open.get(url).reject(new Error("404"));
      open.delete(url);
      await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
    },
  };
}

/* ---- the width of the road ------------------------------------------ */
{
  const h = hand();
  const idles = [];
  const w = warming(h.fetch, (run) => idles.push(run), 2);

  w.warm(["a", "b", "c", "d"]);
  is(h.asked, [], "warming waits for an idle moment — it is not what the "
     + "reader asked for");
  is(idles.length, 1, "and asks for exactly one");

  idles.shift()();
  is(h.asked, ["a", "b"], "two lanes, two fetches, and the rest wait");
  is(w.inFlight(), 2, "two in flight");
  is(w.waiting(), 2, "two still waiting");

  await h.done("a");
  is(h.asked, ["a", "b", "c"], "a lane freed is a lane used");
  await h.done("b");
  await h.done("c");
  is(h.asked, ["a", "b", "c", "d"], "and so on to the end of the queue");
  await h.done("d");
  is(w.waiting(), 0, "nothing left waiting");
  is(w.inFlight(), 0, "nothing left in flight");
}

/* ---- the reader jumps the queue ------------------------------------- */
{
  const h = hand();
  const idles = [];
  const w = warming(h.fetch, (run) => idles.push(run), 1);

  w.warm(["one", "two", "three"]);
  idles.shift()();
  is(h.asked, ["one"], "one lane, one fetch");

  /* The reader opens something. It must be next, not fourth. */
  w.urgent(["opened"]);
  is(h.asked, ["one"], "the lane is full, so nothing starts yet");
  await h.done("one");
  is(h.asked, ["one", "opened"], "what the reader opened goes before the "
     + "rest of the page, however much of it is queued");
  await h.done("opened");
  is(h.asked, ["one", "opened", "two"], "and then the warming carries on");
}

/* ---- a queue that is ITSELF urgent ---------------------------------- */
{
  /* The case above passes for a reason that does not hold on the page:
   * the queue it jumps is in a LOWER tier. Measured on the real page,
   * 148 of the 150 photographs are within three screens of the middle
   * of it — and those were all being promoted to this same tier, so
   * what the reader actually opened joined the back of a queue of 148
   * and "jumps the queue" meant nothing. */
  const h = hand();
  const w = warming(h.fetch, (run) => run(), 1);

  w.urgent(["near-1", "near-2", "near-3"]);
  is(h.asked, ["near-1"], "one lane, one fetch");
  w.urgent(["opened"]);
  await h.done("near-1");
  is(h.asked, ["near-1", "opened"],
     "what the reader just opened is next, even when the queue it joins "
     + "is itself urgent — the most recent thing asked for is the thing "
     + "being waited for");
  await h.done("opened");
  is(h.asked, ["near-1", "opened", "near-2"],
     "and the rest of that tier carries on behind it, in its own order");
}

/* ---- several at once keep their order ------------------------------- */
{
  const h = hand();
  const w = warming(h.fetch, (run) => run(), 1);
  w.urgent(["a", "b", "c"]);
  await h.done("a");
  await h.done("b");
  is(h.asked, ["a", "b", "c"],
     "a project's photographs are fetched in the order they are in, not "
     + "reversed by going to the front");
}

/* ---- urgent does not wait for idle ---------------------------------- */
{
  const h = hand();
  const w = warming(h.fetch, () => { throw new Error("idle was used"); }, 2);
  w.urgent(["now", "also"]);
  is(h.asked, ["now", "also"], "what the reader is looking at is fetched at "
     + "once, without waiting to be idle");
}

/* ---- promotion of something already queued -------------------------- */
{
  const h = hand();
  const idles = [];
  const w = warming(h.fetch, (run) => idles.push(run), 1);

  w.warm(["far", "near"]);
  w.urgent(["near"]);                 // the reader got there first
  idles.shift()();
  is(h.asked, ["near"], "a url already queued is promoted, not queued twice");
  await h.done("near");
  is(h.asked, ["near", "far"], "and the stale entry is skipped when it comes "
     + "up, rather than fetching it again");
  await h.done("far");
  is(h.asked.filter((u) => u === "near").length, 1, "fetched exactly once");
}

/* ---- nothing is fetched twice --------------------------------------- */
{
  const h = hand();
  const idles = [];
  const w = warming(h.fetch, (run) => idles.push(run), 4);

  w.warm(["x", "x", "y"]);
  idles.shift()();
  is(h.asked, ["x", "y"], "the same url twice in one call is one fetch");
  w.urgent(["x"]);
  is(h.asked, ["x", "y"], "and asking for one in flight does not start it "
     + "again");
  await h.done("x");
  w.urgent(["x"]);
  is(h.asked, ["x", "y"], "nor one already done");
  is(w.state.get("x"), "done", "which is what `state` is for");
}

/* ---- one failure, and the queue carries on -------------------------- */
{
  const h = hand();
  const idles = [];
  const w = warming(h.fetch, (run) => idles.push(run), 1);

  w.warm(["bad", "good", "better"]);
  idles.shift()();
  await h.failed("bad");
  is(w.state.get("bad"), "failed", "a failure is recorded");
  is(h.asked, ["bad", "good"], "and the next one starts — 150 photographs "
     + "and one 404 must not take the other 149 with it");
  await h.done("good");
  await h.done("better");
  is(w.waiting(), 0, "the queue drains");

  /* And a failure is worth retrying when the reader actually gets
   * there: a photograph that failed during the warming may well arrive
   * when it is the thing on screen. */
  w.urgent(["bad"]);
  is(h.asked, ["bad", "good", "better", "bad"], "a failed url is retried "
     + "when it is asked for in earnest");
}

/* ---- tiers in between ----------------------------------------------- */
{
  const h = hand();
  const idles = [];
  const w = warming(h.fetch, (run) => idles.push(run), 1);

  w.warm(["rest"], 2);
  w.warm(["probably-next"], 1);
  idles.shift()();
  is(h.asked, ["probably-next"], "the middle tier is for what the reader is "
     + "likely to reach next, and it goes first");
  await h.done("probably-next");
  is(h.asked, ["probably-next", "rest"], "then the rest of the page");
}

/* ---- the fetcher is told how badly it is wanted --------------------- */
{
  const asked = [];
  const idles = [];
  const w = warming((url, wanted) => { asked.push(url + (wanted ? "!" : "")); return Promise.resolve(); },
                    (run) => idles.push(run), 4);

  w.warm(["background"]);
  idles.shift()();
  is(asked, ["background"], "a warmed photograph is fetched without a flag — "
     + "the page turns that into a low fetch priority, so 150 of them are "
     + "never in front of the one being waited for");

  asked.length = 0;
  w.urgent(["wanted"]);
  is(asked, ["wanted!"], "and what the reader is looking at is flagged");
}

/* ---- and whether the big copies are warmed at all ------------------- */
{
  ok(worthWarmingBigCopies(undefined),
     "a browser that says nothing about the connection and is not "
     + "phone-shaped — desktop Safari has no Network Information API — "
     + "gets the big copies, where they cost least");
  ok(!worthWarmingBigCopies(undefined, true),
     "and a PHONE that says nothing does not. Safari is the browser with "
     + "no Network Information API and Safari is also every iPhone, so "
     + "`nothing said` used to mean `desktop` on the one device this is "
     + "meant to protect — 8.3MB of photographs nobody asked for, on the "
     + "device the page is approved on");
  ok(!worthWarmingBigCopies({}, true),
     "an empty hint from a phone is the same case: nothing was measured");
  ok(worthWarmingBigCopies({ effectiveType: "4g" }, true),
     "but a phone that MEASURES 4g still gets them — a measurement beats "
     + "a guess about the shape of the device, and that was always allowed");
  ok(!worthWarmingBigCopies({ saveData: true }, false),
     "and data saver refuses them with no connection class at all, which "
     + "the early return used to skip past");
  ok(worthWarmingBigCopies({ effectiveType: "4g" }), "a fast connection: yes");
  ok(!worthWarmingBigCopies({ saveData: true, effectiveType: "4g" }),
     "data saver says no, however fast the connection is — it is the one "
     + "signal that is a request rather than a measurement");
  ok(!worthWarmingBigCopies({ effectiveType: "3g" }),
     "8.3MB of photographs nobody asked for is not a convenience on 3g");
  ok(!worthWarmingBigCopies({ effectiveType: "slow-2g" }), "nor on slow-2g");
  ok(worthWarmingBigCopies({}),
     "an empty hint is not a refusal: a browser with the API and nothing to "
     + "say about the line is treated like one without it");
}

console.log(`\n  preload: the warming queue holds its order, its width and its `
  + `failures, at ${checks} points\n`);
