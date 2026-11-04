/* How far a photograph has drifted, as a pure function.
 *
 * The movement itself cannot be tested here: it needs a browser that
 * scrolls and runs animation frames, and the headless harness does
 * neither — measured, not assumed (`rafRan=false`, `scrollY=0` after a
 * `scrollTo`).
 *
 * So the arithmetic is separated from the browser and checked on its
 * own. What is left in the page is a `getBoundingClientRect`, a call to
 * this, and a write — the parts a reader can verify by looking.
 */
/** Pixels to move a photograph whose box starts at `top` and is `height`
 *  tall, inside a viewport `viewport` tall, drifting `amount` either way.
 *
 *  Centred in the viewport it sits still. Entering from the bottom it is
 *  pushed down, leaving at the top it is pulled up, and it never exceeds
 *  `amount` in either direction however far off-screen it is. */
export function shiftFor(top, height, viewport, amount) {
    if (viewport <= 0)
        return 0;
    const through = (top + height / 2) / viewport;
    const shift = (0.5 - through) * 2 * amount;
    // Clamped, because a photograph far off-screen would otherwise be
    // translated further than its own height and arrive from nowhere.
    return Math.max(-amount, Math.min(amount, shift));
}
//# sourceMappingURL=drift.js.map