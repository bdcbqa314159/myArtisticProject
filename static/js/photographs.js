/* Every photograph the page holds, fetched before it is looked at.
 *
 * The queue itself is `preload.ts`; this is the page's half of it —
 * what to warm, in what order, and whether the connection can afford
 * the bigger copies at all.
 */
import { warming, worthWarmingBigCopies } from "./preload.js";
import { within } from "./nearby.js";
export const PHOTOGRAPHS = warming((url, wanted) => {
    const img = new Image();
    img.decoding = "async";
    /* A HINT, NOT A QUEUE OF OUR OWN. The browser schedules its own
     * network: telling it that a warming fetch is low and a wanted one
     * is high keeps 150 background photographs from being in front of
     * the one the reader is waiting for. Unknown to Safari, which
     * ignores it. */
    img.fetchPriority =
        wanted ? "high" : "low";
    img.src = url;
    // `decode()` rejects on a broken image, which is what the queue
    // wants to hear; `load` alone would call a half-decodable file
    // ready.
    return img.decode === undefined
        ? new Promise((done, fail) => {
            img.addEventListener("load", () => done());
            img.addEventListener("error", () => fail(new Error(url)));
        })
        : img.decode();
}, (run) => {
    /* Idle if the browser offers it, and a timer if it does not —
     * Safari has no requestIdleCallback. The timeout is a promise that
     * the warming starts even on a page that never goes idle. */
    const idle = window.requestIdleCallback;
    if (idle)
        idle(run, { timeout: 2000 });
    else
        window.setTimeout(run, 200);
});
/** Every photograph the page holds but has not asked for yet.
 *
 *  In two passes, by what the reader is likely to need first: the
 *  copies that are IN the page — the 150 lazy ones, 7.6MB — and then
 *  the bigger copies behind them, which are only ever seen if a
 *  reference or a project is opened.
 *
 *  The second pass is conditional. 8.3MB of photographs nobody has
 *  asked to see is a convenience on a desk and an imposition on a
 *  phone with an allowance, so the browser is asked first. */
export function warmTheRest() {
    const page = [...document.querySelectorAll("img[loading=lazy]")]
        .map((img) => img.currentSrc || img.src);
    PHOTOGRAPHS.warm(page, 1);
    const line = navigator.connection;
    /* Asked of the browser rather than of a user-agent string: a coarse
     * pointer on a small screen. It only decides anything when the
     * connection says nothing at all, which is every iPhone. */
    const phoneLike = matchMedia("(pointer: coarse)").matches
        && Math.min(window.innerWidth, window.innerHeight) <= 600;
    if (!worthWarmingBigCopies(line, phoneLike))
        return;
    const bigger = [...document.querySelectorAll("[data-big]")]
        .map((el) => el.dataset["big"] || "");
    PHOTOGRAPHS.warm(bigger, 2);
}
/* ---- a bigger copy, once it is being looked at ------------------------
 * A print on the card is a card-sized photograph, and the front fills
 * the screen with it: stretched to a 1600px monitor the 900px copy is
 * soft, and on a phone at three device pixels per CSS pixel it is soft
 * as well. The carousel is worse — a photograph someone opened in order
 * to look at it.
 *
 * So the markup carries a second, larger URL in `data-big`, and this
 * fetches it the moment the thing it belongs to opens. Nothing extra is
 * on the first load: a reader who never opens a reference never asks
 * for one of these.
 *
 * THE SMALL ONE STAYS UNTIL THE BIG ONE HAS ARRIVED. Assigning `src`
 * and hoping is how a photograph becomes an empty box on a slow
 * connection — so the big copy is loaded beside the page first and
 * swapped in on its own `load`. `data-big` is removed only then, so a
 * failed fetch leaves the small one in place and can be tried again on
 * the next open.
 */
/* ---- and the queue follows the reader --------------------------------
 * Warming in the order the page is written is right for someone
 * reading from the top and wrong for everyone else: open the menu,
 * jump to Concepts, and the queue is still working through the
 * references above it — so the photographs arrive while they are being
 * looked at, which is the slow motion this is for.
 *
 * So wherever the reader stops, what is within reach is promoted,
 * nearest first. `nearby.ts` does the arithmetic; this measures.
 *
 * On scroll, but not on every scroll event: the positions only matter
 * once the reader has stopped somewhere, and a measurement per frame
 * would be a layout per frame. A quarter of a second after the last
 * one is soon enough to be ahead of a thumb.
 */
const SETTLED_MS = 250;
export function warmWhatIsNear() {
    const lazy = [...document.querySelectorAll("img[loading=lazy]")];
    if (!lazy.length)
        return;
    let waiting = 0;
    const look = () => {
        const placed = lazy.map((img) => {
            const box = img.getBoundingClientRect();
            return {
                url: img.currentSrc || img.src,
                top: box.top + window.scrollY,
                height: box.height,
            };
        });
        /* Three screens rather than two: the sections on this page are
         * long, and two screens of reach can hold nothing at all between
         * one reference and the next.
         *
         * TIER 1, NOT TIER 0. This asked for all of it URGENTLY, which is
         * the tier meaning "the reader is looking at this" — and three
         * screens of this page is almost all of it: measured at the middle
         * of the real page, 148 of the 150 photographs are within reach.
         * So nearly every photograph was being marked as the one being
         * waited for, which made the mark worth nothing in two ways. The
         * browser was told 148 fetches were all `fetchPriority: high`, and
         * a project the reader then opened joined the back of that queue —
         * the opposite of what `work.ts` says happens when it opens one.
         *
         * Tier 1 is this exactly: what the reader is probably about to
         * reach. It still goes before the rest of the page, still nearest
         * first, and it is no longer in front of what they actually did. */
        PHOTOGRAPHS.warm(within(placed, window.scrollY, window.innerHeight, 3), 1);
    };
    look();
    addEventListener("scroll", () => {
        window.clearTimeout(waiting);
        waiting = window.setTimeout(look, SETTLED_MS);
    }, { passive: true });
}
//# sourceMappingURL=photographs.js.map