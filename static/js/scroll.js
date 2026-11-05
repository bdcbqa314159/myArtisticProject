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
export function scrollDuration(distance, min = 480, max = 1100) {
    const d = Math.abs(distance);
    if (!Number.isFinite(d))
        return min;
    return Math.max(min, Math.min(max, min + d * 0.22));
}
/** Eased position between 0 and 1. Slow at both ends, quick through the
 *  middle — the shape a page moving under its own weight would take. */
export function ease(t) {
    const x = t < 0 ? 0 : t > 1 ? 1 : t;
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}
/** Travel to `to`, and call `onSettled` exactly once when the journey
 *  ends — arrived, abandoned by the reader, or replaced by a newer one.
 *
 *  Returns a function that abandons it. */
export function animateScroll(env, to, onSettled) {
    const from = env.position();
    const distance = to - from;
    const ms = scrollDuration(distance);
    const started = env.now();
    let handle = 0;
    let cancelled = false;
    let settled = false;
    const release = env.whenInterrupted(() => { cancelled = true; });
    /* Exactly once, by all three roads out.
     *
     * Twice is reachable without the guard: abandoning runs this, and the
     * frame already in flight then runs it again. Whoever is listening —
     * the navigation band, which is holding its marker still until this
     * says the journey is over — is entitled to assume one. */
    function finish() {
        if (settled)
            return;
        settled = true;
        env.cancelFrame(handle);
        release();
        onSettled?.();
    }
    function step(now) {
        if (cancelled)
            return finish();
        const t = (now - started) / ms;
        env.moveTo(from + distance * ease(t));
        if (t >= 1)
            return finish();
        handle = env.frame(step);
    }
    handle = env.frame(step);
    return () => { cancelled = true; finish(); };
}
//# sourceMappingURL=scroll.js.map