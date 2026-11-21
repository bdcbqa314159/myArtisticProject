/* Every photograph the page holds, fetched before it is looked at.
 *
 * The queue itself is `preload.ts`; this is the page's half of it —
 * what to warm, in what order, and whether the connection can afford
 * the bigger copies at all.
 */
import { warming, worthWarmingBigCopies } from "./preload.js";
export const PHOTOGRAPHS = warming((url) => {
    const img = new Image();
    img.decoding = "async";
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
    if (!worthWarmingBigCopies(line))
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
//# sourceMappingURL=photographs.js.map