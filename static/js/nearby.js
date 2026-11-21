/* What the reader is about to reach.
 *
 * The warming queue fetches the page's photographs in the order they
 * are written, which is the right order for someone reading from the
 * top and the wrong one for everybody else: open the menu, jump to
 * Concepts, and the queue is still working through the references
 * above it. The photographs then arrive while they are being looked
 * at, which is the "slow motion" this is meant to end.
 *
 * So the page says where the reader is, and this says what is nearest.
 * Separated out because it is arithmetic with a lot of edge cases —
 * above the viewport, straddling it, two screens down, a box of zero
 * height while an image has not been measured yet — and none of them
 * can be driven in the browser this repository runs.
 */
/** Those within reach, nearest first.
 *
 *  `reach` is how far ahead to look, in screens. Everything from one
 *  screen ABOVE the viewport is included — a reader scrolling up wants
 *  what is behind them as much as what is in front — and the order is
 *  by distance from the top of the viewport, so the next thing to come
 *  into view is fetched first.
 *
 *  A box of zero height is kept rather than dropped: an image that has
 *  not been laid out yet reports nothing, and it is usually the one
 *  about to matter.
 */
export function within(items, top, height, reach = 2) {
    const from = top - height;
    const to = top + height * reach;
    return [...items]
        .filter((it) => it.url
        && it.top <= to
        && it.top + Math.max(it.height, 1) >= from)
        .map((it) => ({ url: it.url, away: Math.abs(it.top - top) }))
        .sort((a, b) => a.away - b.away)
        .map((it) => it.url);
}
//# sourceMappingURL=nearby.js.map