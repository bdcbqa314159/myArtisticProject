/* Whether this reader has asked for less movement.
 *
 * Read once, here, because every module that moves anything has to
 * agree about it — and because a page that asks the question four
 * times is a page where three of the answers can drift.
 */
export const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
