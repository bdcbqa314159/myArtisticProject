/* The page, started.
 *
 * What is left here is the entry: the cover that holds the page until
 * it is whole, the two small things that belong to no section — the
 * address a visitor can copy, the count of what is still arriving —
 * and the list at the end that starts everything else.
 *
 * The rest moved out, by what it knows about:
 *
 *     motion.ts        how the page moves
 *     nav.ts           getting around it, and the chrome
 *     work.ts          the gallery, opened
 *     photographs.ts   warming them before they are looked at
 *     reduced.ts       the one flag all four consult
 *
 * It was 1547 lines and every piece of work for a month landed in it.
 *
 * THIRTEEN MODULES, AND NO BUNDLER. The page fetches them all — about
 * 85KB of JavaScript — and HTTP/2 carries them on one connection, so
 * the cost is parsing rather than round trips. A bundler would make it
 * one file and would be the first build dependency this repository has
 * ever had; the cover holds the page until everything is in anyway,
 * which is the thing a reader notices.
 */
import { owedBeforeShowing } from "./cover.js";
import { reduced } from "./reduced.js";
import { startMotion, prepareMotion, exchangePhrases, photographsDrift, showTheRelease, softWhileMoving } from "./motion.js";
import { syncBar, WIDE, markCurrentSection, closeMenuOnNavigate, keepOneAddress, tintOnTheWayIn } from "./nav.js";
import { closeTheCarousel, sharpenOnOpen, placeTheLights, levelTheCarousels } from "./work.js";
import { warmTheRest, warmWhatIsNear } from "./photographs.js";
/* ---- blocks arrive on scroll -----------------------------------------
 * In two halves, and the split matters.
 *
 * `.reveal` is `opacity: 0`. Added after the cover had already lifted, it
 * blanked a page the visitor was looking at: the page faded in whole,
 * every block went transparent, and they then faded back one at a time.
 * A page appearing and then vanishing is a far worse first impression
 * than no animation at all.
 *
 * So the marking happens while the cover is still up, and only the
 * observing waits for it to lift.
 */
function copyButtons() {
    for (const btn of document.querySelectorAll("[data-copy]")) {
        // Captured ONCE, outside the handler. Read inside it, a second click
        // within the 2.5s window captured "Copied" as the original label and
        // restored that for ever — the button then lied about what it said.
        const said = btn.textContent;
        let restore = 0;
        btn.addEventListener("click", async () => {
            const value = btn.dataset["copy"];
            if (!value)
                return;
            try {
                await navigator.clipboard.writeText(value);
                btn.textContent = "Copied";
            }
            catch {
                // Clipboard access can be refused, and silently failing would
                // leave someone believing they had the address.
                btn.textContent = "Copy failed — select it by hand";
            }
            clearTimeout(restore);
            restore = window.setTimeout(() => { btn.textContent = said; }, 2500);
        });
    }
}
/* ---- how far along -----------------------------------------------------
 * The cover waits for every image that is not lazy. This counts them
 * and says so, instead of looping an animation that would look the same
 * whatever the wait turned out to be.
 *
 * It runs while the cover is still up, which is the only time it is
 * worth anything. It never reveals the page — there is exactly one
 * place that does, and a second would be how "page, loader, page"
 * happened before.
 */
function countTheWait() {
    const line = document.querySelector(".load-line");
    if (!line)
        return;
    const waited = [...document.querySelectorAll("img")]
        .filter((img) => img.loading !== "lazy");
    if (waited.length === 0) {
        // Nothing to measure. A bar sitting at nothing reads as stuck, so
        // it sweeps instead and says only "still working".
        line.classList.add("unknown");
        return;
    }
    let done = 0;
    const mark = () => {
        line.style.setProperty("--done", String(done / waited.length));
    };
    for (const img of waited) {
        if (img.complete) {
            done += 1;
            continue;
        }
        // `error` as well as `load`: a photograph that fails is still a
        // photograph the page has stopped waiting for, and a bar that
        // stalls at four fifths because one 404'd is worse than no bar.
        const arrived = () => { done += 1; mark(); };
        img.addEventListener("load", arrived, { once: true });
        img.addEventListener("error", arrived, { once: true });
    }
    mark();
}
/* ---- showing the page -------------------------------------------------
 * myBureau's sequence, which is the one that works:
 *
 *   `.is-leaving` keeps the overlay painted while `booting` comes off,
 *   it fades, and then it is REMOVED from the document.
 *
 * Removing it matters. Left in place with `visibility: hidden` it is a
 * covered page one stale class away from being covered again, and it
 * holds a state nothing else can see.
 *
 * The page underneath is finished the whole time — the fade of the cover
 * IS the transition, and nothing else moves with it.
 */
function start(what, step) {
    try {
        step();
    }
    catch (err) {
        // Deliberately not shown on the page. The reader cannot act on it,
        // and a portfolio that explains its own faults to a visitor is
        // worse than one quietly missing an effect.
        console.error(`[landing] ${what} did not start`, err);
    }
}
if (!reduced)
    start("the motion", prepareMotion);
start("the bar", () => {
    syncBar();
    WIDE.addEventListener("change", syncBar);
});
start("the section marker", markCurrentSection);
start("closing the menu on a jump", closeMenuOnNavigate);
start("the copy buttons", copyButtons);
start("the tint on the way in", tintOnTheWayIn);
start("counting the wait", countTheWait);
start("softening while moving", softWhileMoving);
start("the phrases exchanging", exchangePhrases);
start("closing the carousel", closeTheCarousel);
start("the bigger copies", sharpenOnOpen);
start("warming the rest", warmTheRest);
start("warming what is near", warmWhatIsNear);
start("keeping one address", keepOneAddress);
start("the photographs drifting", photographsDrift);
start("the press and release", showTheRelease);
start("placing the lights", placeTheLights);
start("levelling the carousels", levelTheCarousels);
/* LAST, and the ONLY place the page is shown.
 *
 * There must be exactly one of these. There were briefly two — an older
 * `uncover()` alongside this — and they ran in order: the first removed
 * `booting`, which takes the cover away instantly because `.loader` is
 * `display: none` without it; the second then added `.is-leaving`, which
 * put the cover BACK so it could fade. Page, loader, page. If a second
 * way to reveal the page is ever added, this one must go.
 *
 * `load`, not `DOMContentLoaded`: the point of covering the page is to
 * wait for the photographs. With no lazy attribute on them they are all
 * in flight from the start, so this is the moment it is genuinely whole.
 * The 6s failsafe in the head covers anything that goes wrong here. */
/* A FLOOR, so the cover is never a flicker.
 *
 * On a fast connection or a cached reload the page was ready before
 * anyone had seen the cover, and `reveal()` began fading it the instant
 * it appeared — which reads as a flash of something, not as a page
 * arriving. Below this, the cover waits; above it, nothing is added.
 *
 * `performance.now()` is milliseconds since the navigation began, which
 * is as long as the cover can possibly have been up. Comfortably under
 * the 6s failsafe in the head, which must stay the last word. */
const COVER_FLOOR_MS = 450;
/* ---- leaving the top of the page changes the light -------------------
 *
 * "By default we are cream, always. Scrolling does nothing. If the user
 *  clicks on Explore selected work we move to the right section and we
 *  switch to the grey palette. Re-clicking does nothing. If we quit and
 *  come back we are cream again."
 *
 * The door was Explore selected work alone, then Selected Work in the
 * menu as well, and now EVERY entry in the menu — settled with the
 * client. The rule the light states is therefore "you have left the
 * top of the page", not "you have gone into the work". Nothing here
 * changed to do it: the trigger is an attribute on the element, so
 * widening it was a line of the template.
 *
 * All four of those fall out of one line: set the attribute, store
 * nothing. Setting it twice is the same as setting it once, and a
 * reload has no memory to consult — the head used to read a saved
 * palette before first paint and no longer does, which is what makes
 * "quit and come back" reliable rather than hopeful.
 *
 * The tokens change under a short transition, put on and taken off
 * again, so the page warms into the new light instead of flicking. A
 * permanent transition on every element would animate every hover on
 * the page as well.
 */
function reveal() {
    const loader = document.querySelector(".loader");
    if (!loader) {
        document.documentElement.classList.remove("booting");
        return;
    }
    loader.classList.add("is-leaving");
    document.documentElement.classList.remove("booting");
    if (reduced) {
        loader.remove();
        return;
    }
    void loader
        .animate([{ opacity: 1 }, { opacity: 0 }], {
        duration: 420,
        easing: "cubic-bezier(.4,0,.6,1)",
        fill: "forwards",
    })
        .finished.then(() => loader.remove());
}
/* Start at the top, every time.
 *
 * Browsers restore the previous scroll position on reload, which happens
 * underneath the cover — so the cover would lift onto wherever the
 * reader had got to last time, mid-section, with the hero never seen. On
 * a one-page site that is held back until it is whole, the top is the
 * only sensible place to arrive. */
if ("scrollRestoration" in history)
    history.scrollRestoration = "manual";
/* Prepared under the cover, started when it lifts. Doing both at once is
 * what blanked the page after it had already appeared. */
function show() {
    // STILL THE ONLY PLACE THE PAGE IS SHOWN. The wait is in front of the
    // one reveal, not a second way of reaching it.
    // The arithmetic lives in `cover.ts` so it can be checked exactly,
    // rather than by timing the real cover against a virtual clock.
    const owed = owedBeforeShowing(performance.now(), COVER_FLOOR_MS);
    window.setTimeout(() => {
        /* The reveal first, and on its own. Whatever else fails the
         * page must appear — the alternative is a reader looking at a
         * blank cover until the six-second failsafe in the head gives
         * up on us. The motion after it is an ornament by comparison. */
        start("the reveal", reveal);
        if (!reduced)
            start("the motion on arrival", startMotion);
    }, owed);
}
if (document.readyState === "complete")
    show();
else
    window.addEventListener("load", show, { once: true });
//# sourceMappingURL=landing.js.map