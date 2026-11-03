/* Everything moving on this page, with no dependencies.
 *
 * Three effects, which together are the whole motion vocabulary of the
 * reference sites (see _ref/references.md): a fade, a rise, and a
 * word-by-word masked reveal on display headlines.
 *
 * All three degrade to "the page, not moving" rather than to a broken
 * page: the classes are added by this script, so a browser that never
 * runs it shows everything, and reduced motion is honoured by not
 * touching the DOM at all.
 */
import { splitWords } from "./words.js";
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
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
function markReveals() {
    // Everything except the hero. The hero is what the wait was for: when
    // the cover dissolves it should already be there, whole, rather than
    // starting a second animation the moment the first one ends. Blocks
    // further down have not been waited for and can arrive as you reach
    // them.
    for (const el of document.querySelectorAll("section:not(.hero) > .wrap > *")) {
        el.classList.add("reveal");
    }
}
/* One observer for the whole page. `once` is deliberate: a block that has
 * arrived stays arrived, because re-animating on the way back up reads as
 * a glitch rather than as an effect.
 */
function observeReveals() {
    const blocks = document.querySelectorAll(".reveal");
    // Anything already on screen is revealed NOW, synchronously, before a
    // single frame is painted.
    //
    // IntersectionObserver callbacks are asynchronous. Creating the
    // observer and waiting for it means at least one frame where blocks
    // that are plainly in view are still `opacity: 0` — and if the reader
    // is part-way down the page, that frame is a bare ground with nothing
    // on it. On a reload, with the scroll position restored under the
    // cover, that is the whole screen: the loader ends and there is
    // blackness until the callbacks land.
    for (const el of blocks) {
        const box = el.getBoundingClientRect();
        if (box.top < window.innerHeight && box.bottom > 0)
            el.classList.add("in");
    }
    const seen = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (!entry.isIntersecting)
                continue;
            entry.target.classList.add("in");
            seen.unobserve(entry.target);
        }
    }, 
    // Fire a little before the block's top edge arrives, so the motion
    // finishes about where the eye lands rather than after it.
    { rootMargin: "0px 0px -12% 0px", threshold: 0.01 });
    for (const el of blocks)
        seen.observe(el);
}
/* ---- display headlines, word by word ---------------------------------
 * Each word goes in a clipping box with the word inside it pushed below
 * the bottom edge, then released. The stagger is in CSS (nth-child), not
 * here, so no inline style is written and the CSP needs no exception.
 *
 * Only ever applied to headings whose content is plain text. A heading
 * containing a link or an <em> is left exactly as the author wrote it —
 * rebuilding arbitrary inline markup word-wise is a parser, and a
 * headline is not worth a parser.
 */
function splitHeadlines() {
    // DOM surgery only. Nothing is released here — see releaseHeadlines().
    for (const h of document.querySelectorAll("h1, section h2")) {
        if (h.childElementCount > 0)
            continue;
        const text = h.textContent;
        if (!text || !text.trim())
            continue;
        const frag = document.createDocumentFragment();
        for (const part of splitWords(text)) {
            if ("space" in part) {
                frag.append(part.space);
                continue;
            }
            const box = document.createElement("span");
            box.className = "w";
            const inner = document.createElement("span");
            inner.className = "wi";
            inner.textContent = part.word;
            box.append(inner);
            frag.append(box);
        }
        h.replaceChildren(frag);
        h.classList.add("split");
    }
}
/* The release, which waits for the cover to lift. Splitting the words is
 * harmless under the cover; letting them play is not, because an
 * animation nobody can see has simply been spent. */
function releaseHeadlines() {
    for (const h of document.querySelectorAll(".split")) {
        if (h.tagName === "H1") {
            // The hero headline is above the fold by definition, so it goes on
            // the next frame rather than waiting for an observer.
            //
            // Not a micro-optimisation: on a cold Safari launch the page can
            // still be hidden when the observer would have run, and callbacks
            // are deferred until it is visible — which showed up as a blank
            // headline for the first seconds. A portfolio handed to someone on
            // a phone cannot open on an empty hero.
            requestAnimationFrame(() => h.classList.add("in"));
        }
        else {
            // Below the fold, wait for the reader to arrive.
            const seen = new IntersectionObserver((entries) => {
                for (const e of entries) {
                    if (!e.isIntersecting)
                        continue;
                    e.target.classList.add("in");
                    seen.unobserve(e.target);
                }
            }, { threshold: 0.1 });
            seen.observe(h);
        }
    }
    // Failsafe, in the same spirit as the rest: whatever happens to the
    // observers, nothing stays invisible. Four seconds is long past any
    // legitimate reveal and still inside the time someone is looking.
    setTimeout(() => {
        for (const h of document.querySelectorAll(".split"))
            h.classList.add("in");
        for (const el of document.querySelectorAll(".reveal"))
            el.classList.add("in");
    }, 4000);
}
/* ---- the bar ----------------------------------------------------------
 * Above 800px the maquette's bar is an inline row of links; below it,
 * a disclosure. One <details> serves both, but not by styling its
 * closed state: Safari and Chrome now hide a closed details through
 * `::details-content` with `content-visibility`, which no `display`
 * rule on the children can reach. Overriding it worked once and
 * silently stopped working, leaving the desktop bar as a lone wordmark.
 *
 * So the element is genuinely opened instead. Honest, and it cannot be
 * undone by a UA stylesheet.
 */
const WIDE = matchMedia("(min-width: 50rem)");
function syncBar() {
    const menu = document.querySelector(".menu");
    if (!menu)
        return;
    menu.open = WIDE.matches;
}
/* ---- which section you are in -----------------------------------------
 * The link for the section in view is marked, so the bar says where you
 * are rather than only where you could go. Cheap: one observer, no
 * scroll handler.
 *
 * The band near the top is deliberately narrow — a section counts as
 * "current" while its heading is in the upper part of the screen, which
 * is where a reader's attention is, rather than whenever any pixel of it
 * is visible. Without that, two sections are current at once on a tall
 * desktop window and the mark flickers between them.
 */
function markCurrentSection() {
    const links = new Map();
    for (const a of document.querySelectorAll(".links a")) {
        const id = a.getAttribute("href")?.replace("#", "");
        if (id)
            links.set(id, a);
    }
    if (links.size === 0)
        return;
    const seen = new IntersectionObserver((entries) => {
        for (const e of entries) {
            const a = links.get(e.target.id);
            if (!a)
                continue;
            a.classList.toggle("current", e.isIntersecting);
        }
    }, { rootMargin: "-10% 0px -70% 0px" });
    for (const id of links.keys()) {
        const section = document.getElementById(id);
        if (section)
            seen.observe(section);
    }
}
/* ---- the menu closes behind you --------------------------------------
 * <details> does the opening, the closing and the keyboard on its own.
 * The one thing it cannot know is that following an anchor means the
 * reader is done with it — leave it open and the panel sits on top of
 * the section they just asked for.
 */
function closeMenuOnNavigate() {
    const menu = document.querySelector(".menu");
    if (!menu)
        return;
    menu.addEventListener("click", (ev) => {
        // Only below the breakpoint. Closing it on a wide screen would take
        // the whole bar away on the first click.
        if (WIDE.matches)
            return;
        if (ev.target.closest(".links a"))
            menu.open = false;
    });
}
/* ---- copy the address -------------------------------------------------
 * Only ever rendered when a verified address is configured, so there is
 * nothing here to copy while the contact section is in its pending state.
 */
function copyButtons() {
    for (const btn of document.querySelectorAll("[data-copy]")) {
        btn.addEventListener("click", async () => {
            const value = btn.dataset["copy"];
            if (!value)
                return;
            const said = btn.textContent;
            try {
                await navigator.clipboard.writeText(value);
                btn.textContent = "Copied";
            }
            catch {
                // Clipboard access can be refused, and silently failing would
                // leave someone believing they had the address.
                btn.textContent = "Copy failed — select it by hand";
            }
            setTimeout(() => { btn.textContent = said; }, 2500);
        });
    }
}
/* Script is present. The bar's wide-screen styling depends on this
 * class, so that with no script the disclosure button stays visible and
 * the menu still works natively — hiding the button and relying on JS to
 * open the panel would leave a scriptless visitor with no navigation at
 * all. No flash: the loader is still over the page when this runs. */
document.documentElement.classList.add("js");
/* Start at the top, every time.
 *
 * Browsers restore the previous scroll position on reload, which happens
 * underneath the cover — so the cover would lift onto wherever the
 * reader had got to last time, mid-section, with the hero never seen. On
 * a one-page site that is held back until it is whole, the top is the
 * only sensible place to arrive. */
if ("scrollRestoration" in history)
    history.scrollRestoration = "manual";
/* Marked, then started. Still two steps: the marking must be in place
 * before anything observes it, and observeReveals() reveals whatever is
 * already on screen synchronously, so no frame is painted with visible
 * content still transparent. */
function prepareMotion() {
    splitHeadlines();
    markReveals();
}
function startMotion() {
    releaseHeadlines();
    observeReveals();
}
if (!reduced) {
    prepareMotion();
    startMotion();
}
syncBar();
WIDE.addEventListener("change", syncBar);
markCurrentSection();
closeMenuOnNavigate();
copyButtons();
//# sourceMappingURL=landing.js.map