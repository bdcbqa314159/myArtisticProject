/* How long a scroll should take, as a pure function.
 *
 * The motion itself needs a browser that scrolls and runs animation
 * frames, and the headless one does neither — measured, not assumed. So
 * the arithmetic is separated out and checked on its own, and what is
 * left in the page is a loop that reads a clock and sets `scrollTop`.
 */

/** Milliseconds for a scroll of `distance` pixels.
 *
 *  Not a fixed duration: the same number of milliseconds makes a jump
 *  to the next section feel sluggish and a jump to the foot of the page
 *  feel frantic. Proportional, then clamped at both ends — slow enough
 *  to be followed, never slow enough to be waited for. */
export function scrollDuration(distance: number, min = 480, max = 1100): number {
  const d = Math.abs(distance);
  if (!Number.isFinite(d)) return min;
  return Math.max(min, Math.min(max, min + d * 0.22));
}

/** Eased position between 0 and 1. Slow at both ends, quick through the
 *  middle — the shape a page moving under its own weight would take. */
export function ease(t: number): number {
  const x = t < 0 ? 0 : t > 1 ? 1 : t;
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}
