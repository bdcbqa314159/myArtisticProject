/* How long the cover still owes the reader, as a pure function.
 *
 * Separated out for the same reason `scroll.ts` was: the thing worth
 * checking is arithmetic, and it was being checked by timing the real
 * cover in a real browser against a virtual clock. That measurement
 * failed twice — once reporting 41ms and once 5026ms, both on a page
 * that was behaving perfectly — because a loaded machine under a
 * virtual clock cannot be asked how long something took.
 *
 * It can be asked whether the cover appeared and whether it left. The
 * duration belongs here, where it can be answered exactly.
 */

/** Milliseconds the cover must stay before it may be taken away.
 *
 *  On a fast connection or a cached reload the page is ready before
 *  anyone has seen the cover, and revealing immediately reads as a
 *  flash of something rather than as a page arriving. Below the floor
 *  the cover waits; above it, nothing is added.
 *
 *  `since` is milliseconds since the navigation began — which is as
 *  long as the cover can possibly have been up already. */
export function owedBeforeShowing(since: number, floor: number): number {
  // A clock that has not started, or one that has gone backwards, owes
  // the whole floor rather than a negative wait or a NaN.
  if (!Number.isFinite(since) || since < 0) return floor;
  if (!Number.isFinite(floor) || floor <= 0) return 0;
  return Math.max(0, floor - since);
}
