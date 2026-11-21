/* One horizon for a project's photographs.
 *
 * On a wide screen they already share one: the slide is short and wide,
 * so the HEIGHT is what binds every photograph and they all come out
 * the same — "they are all uniform in size", which is what was asked
 * for. On a phone the slide is tall and narrow, so the WIDTH binds
 * instead and an upright photograph comes out twice the height of a
 * landscape one. Same rule, different shape of screen, and the result
 * reads as an accident.
 *
 * So the horizon is chosen rather than fallen into: the tallest every
 * photograph can be while the WIDEST of them still fits the slide.
 * Nothing is cropped and nothing is enlarged; a landscape photograph
 * fills the width, an upright one is narrower, and the two share a
 * height.
 *
 * It costs the upright ones their size on a phone — 195x260 where they
 * were 390x520 — which is the price of uniformity without cropping.
 * `object-fit: cover` would make them identical AND large, and would
 * cut the sides off every landscape photograph.
 */
/** The common height, in pixels.
 *
 *  `aspects` are width ÷ height of each photograph. The slide is the
 *  box they have to fit in.
 */
export function horizonFor(aspects, width, height, ceiling = Infinity) {
    const real = [...aspects].filter((a) => Number.isFinite(a) && a > 0);
    if (!real.length || width <= 0 || height <= 0)
        return height > 0 ? height : 0;
    // The widest photograph decides: at this height it exactly fills the
    // slide's width, and every narrower one has room to spare.
    const widest = Math.max(...real);
    /* AND NOTHING IS ENLARGED TO MEET IT. `ceiling` is the shortest
     * photograph's own pixel height: forcing a common height taller than
     * that would stretch it, which is the one thing none of this is
     * allowed to do. Caught by the check that measures it — a 667px
     * photograph drawn 801px tall to match the slide.
     *
     * It rarely binds. A photograph of 2000px on the long edge is taller
     * than any slide; it is the 1000px stand-ins that run out first, and
     * `content-check.py` says so at the gate. */
    const limit = Number.isFinite(ceiling) && ceiling > 0 ? ceiling : Infinity;
    return Math.min(height, width / widest, limit);
}
//# sourceMappingURL=horizon.js.map