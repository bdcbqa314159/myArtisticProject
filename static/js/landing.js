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
import { shiftFor } from "./drift.js";
/* Both failsafes in one place, so the ordering between them is visible.
 * The cover's lives in the inline script in the head and is 6000ms;
 * this one must come after it. */
const MOTION_FAILSAFE_MS = 7000;
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
    // Failsafe: whatever happens to the observers, nothing stays
    // invisible.
    //
    // AFTER the cover's own failsafe, deliberately. The inline script in
    // the head uncovers the page at 6s if this script never got that far;
    // firing this at 4s would release the motion while the cover is still
    // up, spending it on a page nobody can see — which is the exact
    // failure the motion was moved out of the cover to avoid.
    setTimeout(() => {
        for (const h of document.querySelectorAll(".split"))
            h.classList.add("in");
        for (const el of document.querySelectorAll(".reveal"))
            el.classList.add("in");
    }, MOTION_FAILSAFE_MS);
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
/* ---- the photographs drift ---------------------------------------------
 * "Ajouter un léger mouvement vertical lié au scroll (parallax)."
 *
 * Each photograph moves a little against the page as it passes — 14px
 * either side of centre, which is an eighth of its own height and reads
 * as depth rather than as a thing sliding about.
 *
 * The container already clips, and the image is scaled slightly in CSS,
 * so the movement never pulls an edge into view.
 *
 * ON COST, since this is the third thing now running on the same
 * scroll, after the blur and the nav's current-section marking:
 *
 *   - only photographs CURRENTLY ON SCREEN are touched. An observer
 *     keeps the set; the rest are not measured, not written to, not
 *     thought about.
 *   - one frame is requested per scroll event at most, and coalesced —
 *     a burst of scroll events produces one write, not twenty.
 *   - nothing animates when the page is still. There is no running
 *     loop; a frame happens because something moved.
 *   - `transform` only. Never `top`, never `margin`: those are layout,
 *     and layout during a scroll is how a page starts to stutter.
 */
const PARALLAX_PX = 14;
/* ---- the smear ---------------------------------------------------------
 * "J'aimerais simplement ajouter cette petite traînée directionnelle,
 *  presque liquide, qui accompagne le mouvement de l'image. Sur une
 *  seule transition photographique."
 *
 * One photograph, and the trail follows the scroll.
 *
 * The amount is velocity, not position: it grows as the page moves
 * faster and falls to nothing the moment it stops — which is what makes
 * it read as the image being dragged rather than as a style applied to
 * it. The offset carries the sign, so the trail is always behind the
 * direction of travel.
 *
 * Capped, because velocity is unbounded — a flick on a phone can be
 * thousands of pixels a second, and an uncapped smear would turn a
 * photograph into a smudge the length of the screen.
 */
const SMEAR_MAX = 7; // the most it ever blurs, in px — looked at, not guessed
const SMEAR_PER_PX = 0.08; // blur per pixel of movement in one frame
const SVG_NS = "http://www.w3.org/2000/svg";
function smear() {
    /* The filter is BUILT HERE rather than written in the template, for
     * two reasons that each cost a feature on their own:
     *
     * 1. `minify_html` lowercases inline SVG element names —
     *    `feGaussianBlur` came out as `fegaussianblur`. SVG is
     *    case-sensitive, so the filter was inert in the built page while
     *    looking perfectly correct in the source. `createElementNS` is
     *    not something a minifier can reach.
     *
     * 2. `filter: url(#smear)` pointing at a filter that does not exist
     *    is an error, and an element in error IS NOT RENDERED. Written in
     *    CSS against markup, a browser with no JavaScript would have shown
     *    a blank space where the photograph is. Built and applied
     *    together here, no script means no class, no filter, and an
     *    ordinary photograph.
     */
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", "filters");
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    svg.setAttribute("aria-hidden", "true");
    const filter = document.createElementNS(SVG_NS, "filter");
    filter.setAttribute("id", "smear");
    // Room for the trail to exist outside the image's own box.
    filter.setAttribute("x", "-20%");
    filter.setAttribute("y", "-40%");
    filter.setAttribute("width", "140%");
    filter.setAttribute("height", "180%");
    filter.setAttribute("color-interpolation-filters", "sRGB");
    const blur = document.createElementNS(SVG_NS, "feGaussianBlur");
    blur.setAttribute("in", "SourceGraphic");
    blur.setAttribute("stdDeviation", "0 0");
    blur.setAttribute("result", "smeared");
    const offset = document.createElementNS(SVG_NS, "feOffset");
    offset.setAttribute("in", "smeared");
    offset.setAttribute("dx", "0");
    offset.setAttribute("dy", "0");
    filter.append(blur, offset);
    svg.append(filter);
    document.body.append(svg);
    // One photograph, as asked. The class goes on with the filter, so the
    // two can never exist without each other.
    const first = document.querySelector(".case .image img");
    if (!first)
        return null;
    first.classList.add("smear");
    return (velocity) => {
        const amount = Math.min(SMEAR_MAX, Math.abs(velocity) * SMEAR_PER_PX);
        blur.setAttribute("stdDeviation", `0 ${amount.toFixed(2)}`);
        // Behind the movement: scrolling down drags the trail upward.
        offset.setAttribute("dy", (-Math.sign(velocity) * amount * 0.7).toFixed(2));
    };
}
function photographsDrift() {
    if (reduced)
        return;
    const shots = document.querySelectorAll(".case .image img");
    if (shots.length === 0)
        return;
    const onScreen = new Set();
    const smearTo = smear();
    let frame = 0;
    let lastY = window.scrollY;
    function draw() {
        frame = 0;
        const height = window.innerHeight;
        // How far the page moved since the last frame. One subtraction, and
        // it is the only thing the smear needs.
        const velocity = window.scrollY - lastY;
        lastY = window.scrollY;
        if (smearTo)
            smearTo(velocity);
        for (const img of onScreen) {
            const box = img.getBoundingClientRect();
            const shift = shiftFor(box.top, box.height, height, PARALLAX_PX);
            img.style.transform = `translate3d(0, ${shift.toFixed(1)}px, 0)`;
        }
    }
    function request() {
        if (!frame && onScreen.size > 0)
            frame = requestAnimationFrame(draw);
    }
    const seen = new IntersectionObserver((entries) => {
        for (const e of entries) {
            const img = e.target;
            if (e.isIntersecting) {
                onScreen.add(img);
            }
            else {
                onScreen.delete(img);
                // Left where it was, it would be caught mid-drift the next
                // time it came back.
                img.style.transform = "";
            }
        }
        request();
    }, 
    // A little early, so a photograph is already placed when its first
    // pixel appears rather than jumping into position.
    { rootMargin: "120px 0px" });
    for (const img of shots)
        seen.observe(img);
    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", request, { passive: true });
    // The page stops between frames, not on an event, so the last frame
    // can leave a smear frozen on a still photograph. This settles it.
    let settle = 0;
    addEventListener("scroll", () => {
        clearTimeout(settle);
        settle = window.setTimeout(() => smearTo?.(0), 120);
    }, { passive: true });
}
/* ---- one address ------------------------------------------------------
 * THE STALE FRAGMENT.
 *
 * The page used to write `#contact` into the URL when you went there.
 * Scrolling away did not take it off again, so within seconds the
 * address named a section the reader was no longer looking at — and
 * worse, A LINK WHOSE TARGET EQUALS THE CURRENT FRAGMENT IS A NO-OP.
 * The browser has nothing to navigate to, so the link simply dies. That
 * is why the navigation band stopped working after one use while the
 * two hero buttons kept going: the buttons were intercepted here and
 * the band's links were ordinary anchors.
 *
 * A one-page site has one address. So every in-page link is handled
 * here and NOTHING is written to the URL: it stays at `/`, no link can
 * ever be a no-op, and Back leaves the page instead of hopping between
 * places the reader never went.
 *
 * Where the reader is was never the fragment's job anyway —
 * `markCurrentSection()` already marks the band, from what is actually
 * on screen.
 *
 * Reduced motion is handled INSIDE rather than by bailing out: bailing
 * out would hand those readers back to the native anchors, and the bug
 * with them.
 */
const PRESS_MS = 140;
function keepOneAddress() {
    // A fragment we arrived with still works — someone may have been sent
    // `/#work`. The browser jumps to it, and then it is taken off the
    // address so it cannot go stale. Deep links in, clean URL after.
    if (location.hash) {
        // A timer rather than an animation frame. The browser's own jump has
        // already happened by `load`; this only has to be after it, and a
        // frame is both less certain and — measured — something a headless
        // browser never runs, which would leave this untestable.
        setTimeout(() => {
            history.replaceState(null, "", location.pathname + location.search);
        }, 0);
    }
    for (const a of document.querySelectorAll('a[href^="#"]')) {
        a.addEventListener("click", (ev) => {
            const id = a.getAttribute("href")?.slice(1);
            const target = id ? document.getElementById(id) : null;
            if (!target)
                return; // let the browser deal with it
            ev.preventDefault();
            // Only the buttons wait. They have a press to finish — the nav
            // band has nothing to show, and a pause there is just a delay.
            const wait = !reduced && a.classList.contains("btn") ? PRESS_MS : 0;
            setTimeout(() => {
                target.scrollIntoView({
                    behavior: reduced ? "auto" : "smooth",
                    block: "start",
                });
            }, wait);
        });
    }
}
/* ---- soft while moving ------------------------------------------------
 * "Les images sont légèrement floues pendant qu'on fait défiler la page,
 * puis deviennent nettes quand on s'arrête dessus."
 *
 * A class while the page is moving, taken off once it settles. The blur
 * itself is CSS.
 *
 * On cost, because this is the one request that could hurt: the blur
 * does not CHANGE during a scroll, it is simply on. A filter with a
 * constant value is rasterised once and then composited, so the scroll
 * itself stays cheap — the work happens at the two transitions, when
 * the page is not moving. Animating the radius with scroll position
 * would be the expensive version, and is not what was asked for.
 */
const SETTLE_MS = 160;
function softWhileMoving() {
    // Under reduced motion there is no blur at all: for some readers this
    // is not an effect, it is motion sickness.
    if (reduced)
        return;
    const root = document.documentElement;
    let settle = 0;
    addEventListener("scroll", () => {
        if (!root.classList.contains("scrolling"))
            root.classList.add("scrolling");
        clearTimeout(settle);
        settle = window.setTimeout(() => root.classList.remove("scrolling"), SETTLE_MS);
    }, { passive: true });
}
/* ---- choosing a palette -----------------------------------------------
 * An instrument for deciding, not a feature: the control is only
 * rendered while `live = false`, and the finished site has one palette.
 *
 * Switching RELOADS the page rather than swapping the tokens in place.
 * That is deliberate and it is the cheaper answer:
 *
 *   - the loader appears by itself, which is the "waiting animation in
 *     between" that was asked for. No second mechanism, no second thing
 *     that can get the sequence wrong.
 *   - the choice is read before first paint by the inline script in the
 *     head, so the page arrives already in its palette instead of
 *     changing colour after it has been seen.
 *
 * Swapping tokens live would avoid the reload and reintroduce exactly
 * the class of bug that cost most of a day: two things changing the
 * page's appearance at once.
 */
const PALETTES = ["cool", "cream"];
function paletteControl() {
    const button = document.querySelector("[data-palette-toggle]");
    if (!button)
        return;
    // `noUncheckedIndexedAccess` is on, so an index is `string | undefined`
    // whatever the array literally holds. The fallbacks are not defensive
    // noise — they are what makes this compile honestly.
    const current = document.documentElement.dataset["palette"] ?? PALETTES[0] ?? "cool";
    const after = PALETTES[(PALETTES.indexOf(current) + 1) % PALETTES.length];
    const next = after ?? "cool";
    button.textContent = `Palette: ${current} → ${next}`;
    button.addEventListener("click", () => {
        try {
            localStorage.setItem("palette", next);
        }
        catch {
            // Private browsing refuses storage. Switch for this view anyway
            // rather than appearing to do nothing.
            document.documentElement.dataset["palette"] = next;
            return;
        }
        location.reload();
    });
}
/* ---- copy the address -------------------------------------------------
 * Only ever rendered when a verified address is configured, so there is
 * nothing here to copy while the contact section is in its pending state.
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
function prepareMotion() {
    splitHeadlines();
    markReveals();
}
function startMotion() {
    releaseHeadlines();
    observeReveals();
}
if (!reduced)
    prepareMotion();
syncBar();
WIDE.addEventListener("change", syncBar);
markCurrentSection();
closeMenuOnNavigate();
copyButtons();
paletteControl();
softWhileMoving();
keepOneAddress();
photographsDrift();
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
function show() {
    reveal();
    if (!reduced)
        startMotion();
}
if (document.readyState === "complete")
    show();
else
    window.addEventListener("load", show, { once: true });
//# sourceMappingURL=landing.js.map