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
import { animateScroll } from "./scroll.js";
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
/* The marker's own controls, so navigation can speak to it.
 * Set when markCurrentSection runs; null if the band has no links. */
let marker = null;
function markCurrentSection() {
    const links = new Map();
    for (const a of document.querySelectorAll(".links a")) {
        const id = a.getAttribute("href")?.replace("#", "");
        if (id)
            links.set(id, a);
    }
    if (links.size === 0)
        return;
    const sections = [];
    for (const id of links.keys()) {
        const el = document.getElementById(id);
        if (el)
            sections.push([id, el]);
    }
    if (sections.length === 0)
        return;
    let marked = "";
    /* While a click is being honoured, the scroll is not in charge.
     *
     * A smooth scroll from the top to Contact passes through every
     * section on the way, and a marker following the scroll walks the
     * whole band one link at a time before settling — which looks like
     * indecision. A click already says where the reader is going, so the
     * answer is known before the journey starts. */
    let locked = "";
    let unlock = 0;
    /* EXACTLY ONE section is current.
     *
     * It used to be each section deciding for itself, through an observer
     * whose band was a fifth of the screen tall. Two consequences, both
     * reported:
     *
     *   - where the band spanned a boundary, TWO sections were inside it
     *     and both were underlined
     *   - the LAST section could never get in. At the bottom of the page
     *     there is no scroll left to bring Contact up into a band that
     *     sits near the top of the screen, so it was never marked at all
     *
     * Independent toggles cannot answer "which one", because that is a
     * question about all of them. So the set is read and one winner is
     * chosen: the last section that has started, and at the foot of the
     * page, the last section outright — because that is where the reader
     * plainly is, whatever a band says.
     */
    function pick() {
        if (locked) {
            apply(locked);
            return;
        }
        const line = window.innerHeight * 0.25;
        const atBottom = window.scrollY + window.innerHeight >=
            document.documentElement.scrollHeight - 2;
        // Read every top first, write one class after — no layout thrash.
        const tops = sections.map(([id, el]) => [id, el.getBoundingClientRect().top]);
        let current = "";
        if (atBottom) {
            current = tops[tops.length - 1]?.[0] ?? "";
        }
        else {
            for (const [id, top] of tops) {
                if (top <= line)
                    current = id;
            }
        }
        apply(current);
    }
    function apply(current) {
        if (current === marked)
            return;
        marked = current;
        for (const [id, a] of links) {
            const on = id === current;
            a.classList.toggle("current", on);
            // The same fact, for a reader who cannot see the rule under it.
            if (on)
                a.setAttribute("aria-current", "true");
            else
                a.removeAttribute("aria-current");
        }
    }
    /* Throttled on a clock, not on a frame.
     *
     * An underline does not need frame precision — 80ms is four frames,
     * and nobody has ever noticed a marker arriving a twentieth of a
     * second late. A timer is also the version that can be TESTED: a
     * headless browser never runs animation frames, so an
     * rAF-coalesced marker is a marker no check here can ever observe.
     *
     * Leading and trailing: it moves at once when a scroll starts, and
     * once more when it stops, so it is never left behind. */
    let last = 0;
    let trailing = 0;
    function request() {
        const now = Date.now();
        clearTimeout(trailing);
        if (now - last >= 80) {
            last = now;
            pick();
        }
        else {
            trailing = window.setTimeout(request, 80 - (now - last));
        }
    }
    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", request, { passive: true });
    pick();
    marker = {
        /* Held from the click until the journey ends — however it ends.
         *
         * This used to be a 900ms timer, which was a guess at how long the
         * BROWSER's smooth scroll took. We now run the scroll ourselves and
         * it lasts up to 1100ms, so the guess was short: every jump over
         * about 1200px — which is every jump on a phone — released the
         * marker while the page was still moving, and it walked the band
         * for the last third of the trip. That walk is the exact thing the
         * lock exists to prevent.
         *
         * A duration would fix that arithmetic and still be wrong in the
         * other direction: a reader who flicks the page mid-flight cancels
         * the scroll, and a lock held to its full term then points at a
         * destination nobody is travelling to any more.
         *
         * So it is not a duration. `release()` is called by the scroll when
         * it settles, and a cancelled scroll settles too.
         */
        lock(id) {
            if (!links.has(id))
                return;
            locked = id;
            apply(id);
            // A backstop, and only that. If the scroll never reports back —
            // an exception between the click and the first frame — the band
            // heals itself instead of staying wrong for the rest of the
            // visit. Deliberately far longer than any real scroll, so it can
            // never be what ordinarily ends the lock.
            clearTimeout(unlock);
            unlock = window.setTimeout(() => marker?.release(id), 3000);
        },
        /* Released by the journey that locked it, and by no other.
         *
         * A second click while the first scroll is still running locks the
         * band on the new section and then abandons the old journey — which
         * settles, as it must, and reports its ending. Without this test
         * that ending would release the lock the NEW click had just taken,
         * and two quick taps would leave the band following the scroll
         * again: the original complaint, reintroduced by the fix for it.
         */
        release(id) {
            if (!locked || locked !== id)
                return;
            clearTimeout(unlock);
            locked = "";
            request();
        },
    };
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
/* ---- the release ------------------------------------------------------
 * `:active` lasts as long as the button is held, which on a quick click
 * is under 80ms — so the press was real and nobody saw it. This plays
 * the return AFTER the button is let go, which is the half a person is
 * actually looking at.
 *
 * A class rather than a transition, so it can be retriggered: clicking
 * twice quickly should animate twice, and a transition that is already
 * at its end does nothing.
 */
function showTheRelease() {
    if (reduced)
        return;
    for (const btn of document.querySelectorAll(".btn")) {
        btn.addEventListener("pointerup", () => {
            btn.classList.remove("released");
            // Reading the layout is what makes the removal take effect before
            // the class goes back on; without it the browser coalesces both
            // into no change at all and the animation never restarts.
            void btn.offsetWidth;
            btn.classList.add("released");
        });
        btn.addEventListener("animationend", () => btn.classList.remove("released"));
    }
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
/* ---- one scroll, ours --------------------------------------------------
 * Both the band and the buttons used `scrollIntoView({behavior:
 * "smooth"})`. That hands the speed to the browser, which chooses it
 * differently depending on the distance and differently again between
 * Safari and Chrome — so the two never matched, and neither could be
 * slowed.
 *
 * This is the same movement for every in-page link, at a speed we set.
 *
 * It yields to the reader: a wheel, a touch or a key during the
 * animation stops it where it is. A page that keeps travelling after
 * someone has started scrolling themselves is fighting them.
 */
let stopScrolling = null;
/* The browser's half of the scroll: a clock, a frame scheduler, a
 * scrollbar, and the three events that mean "I'll take it from here".
 * The loop itself is in scroll.ts, where it can be tested. */
const INTERRUPTIONS = ["wheel", "touchstart", "keydown"];
const browserScroll = {
    now: () => performance.now(),
    position: () => window.scrollY,
    moveTo: (y) => window.scrollTo(0, y),
    frame: (cb) => requestAnimationFrame(cb),
    cancelFrame: (h) => cancelAnimationFrame(h),
    whenInterrupted(give) {
        for (const ev of INTERRUPTIONS) {
            addEventListener(ev, give, { passive: true, once: true });
        }
        return () => {
            for (const ev of INTERRUPTIONS)
                removeEventListener(ev, give);
        };
    },
};
/* ---- crossing, for the band -------------------------------------------
 *
 * "Interaction from the menu should lead us in a more smooth way,
 *  without seeing the whole movement."
 *
 * The page softens, moves while nobody can read it, and clears again
 * onto the section asked for. The move itself is instant and that is
 * the point — a reader who asks for About wants About, not a tour of
 * everything above it.
 *
 * `setTimeout`, not `transitionend`: a transition that never fires —
 * because the tab was in the background, because reduced motion took
 * the veil away — would strand the page behind it for ever. A clock
 * always goes off.
 *
 * The buttons keep their long scroll. That journey is the point there,
 * and it is the one the client likes.
 */
const VEIL_IN_MS = 240; // matches the stylesheet's going
const VEIL_OUT_MS = 520; // and its arriving
function crossTo(top, onDone) {
    const root = document.documentElement;
    // Nothing to hide behind: go straight there.
    if (reduced) {
        window.scrollTo(0, top);
        onDone();
        return;
    }
    root.classList.add("crossing");
    window.setTimeout(() => {
        /* Instant, and unseen: everything on screen is already illegible.
         *
         * `behavior: "instant"` and not the two-argument form, which obeys
         * the stylesheet — and the stylesheet says `scroll-behavior:
         * smooth`. Measured: the page did not move at all, because the
         * smooth scroll it asked for needs animation frames the probe's
         * iframe never runs. On a real screen it would have been worse than
         * nothing: a second-long journey underneath a veil that clears in
         * half that, so the reader watches the end of exactly the movement
         * this was built to hide. */
        window.scrollTo({ top, behavior: "instant" });
        root.classList.add("arrived");
        window.setTimeout(() => {
            root.classList.remove("crossing", "arrived");
            onDone();
        }, VEIL_OUT_MS);
    }, VEIL_IN_MS);
}
function scrollTo(top, onSettled) {
    // A newer journey replaces an older one, and the older one settles
    // rather than being dropped — whoever was waiting on it still gets
    // its ending.
    stopScrolling?.();
    if (reduced) {
        window.scrollTo(0, top);
        onSettled?.();
        return;
    }
    const abandon = animateScroll(browserScroll, top, () => {
        stopScrolling = null;
        onSettled?.();
    });
    stopScrolling = abandon;
}
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
            /* A button that opens the form is not a journey. Its `#talk` is
             * the no-script fallback — the dialog shown where it stands — and
             * with script `contact.ts` owns the click entirely.
             *
             * Treating it as a scroll target put a blue ring around the open
             * form: the focus further down is meant to move the keyboard into
             * a SECTION, and run on the dialog it both fought `showModal`,
             * which had already placed focus properly, and drew the browser's
             * own focus outline around the whole window. Measured, from both
             * openers: `outline: 1px auto rgb(153, 200, 255)` on `dialog#talk`. */
            if (a.hasAttribute("data-talk"))
                return;
            ev.preventDefault();
            // The band knows where we are going before we get there.
            marker?.lock(id);
            // Only the buttons wait. They have a press to finish — the nav
            // band has nothing to show, and a pause there is just a delay.
            const wait = !reduced && a.classList.contains("btn") ? PRESS_MS : 0;
            setTimeout(() => {
                // Where the section's top should come to rest: under the bar,
                // which is what `scroll-margin-top` was doing for the native
                // version and has to be done by hand now.
                const bar = document.querySelector("header");
                const offset = bar ? bar.getBoundingClientRect().height : 0;
                /* Contact IS the form. Asked for straight away, not at the
                 * end of the journey — waiting a second for it while the page
                 * slides underneath is the delay, not the arrival.
                 *
                 * The scroll still runs, behind the blur: nobody watches it, but
                 * it is what leaves the reader at Contact when they close the
                 * form rather than back where they set off from. The form lives
                 * in another module; an event is how this one asks for it
                 * without knowing anything about it. */
                if (id === "contact")
                    dispatchEvent(new CustomEvent("talk:open"));
                const landing = window.scrollY + target.getBoundingClientRect().top - offset;
                /* The band crosses; everything else travels. `closest` rather
                 * than a class on the link, because what decides this is where
                 * the link LIVES — a navigation band — not how it is dressed. */
                if (a.closest(".links") !== null) {
                    crossTo(landing, () => marker?.release(id));
                }
                else {
                    scrollTo(landing, 
                    // The band stops guessing where the reader is the moment the
                    // journey actually ends — arrived, or abandoned.
                    () => marker?.release(id));
                }
                // And the keyboard follows the page.
                //
                // Without this the focus stays on the link that was just used,
                // so the next Tab walks further along the navigation band rather
                // than into the section the visitor asked for — the page moves
                // and the keyboard does not. The sections carry `tabindex="-1"`
                // so they can be focused deliberately without ever entering the
                // tab order themselves.
                target.focus({ preventScroll: true });
            }, wait);
        });
    }
}
/* ---- the two phrases exchange places ------------------------------------
 * "Animer les 2 phrases pour qu'elles échangent visiblement leurs
 *  positions. Déclencher l'échange une seule fois à l'apparition de la
 *  section, sans boucle."
 *
 * The heading is written in its FINAL order, which is the order a
 * browser running no script displays and the order a reader is left
 * with. The crossing is the opening state, put there by this function:
 * the phrases start in each other's places and travel home.
 *
 * It has to be that way round. A swap that ENDS crossed would leave the
 * sentence reversed for everyone who stayed on the page, and reversed
 * permanently for anyone whose script never ran.
 *
 * MEASURED, NOT DECLARED. The distance is the gap between the two
 * phrases' own tops, read from the page. A percentage would assume they
 * are the same height, and they are not: they are different lengths and
 * wrap at different widths. Reading it costs one layout, once, before
 * anything has moved.
 *
 * Once, and never again — `unobserve` on the first crossing, and the
 * transition is removed with the class that carried it.
 */
const SWAP_DONE_MS = 1400; // the 820ms journey plus its 480ms delay, rounded up
function exchangePhrases() {
    // No crossing at all under reduced motion: the heading is simply the
    // heading, already in the right order.
    if (reduced)
        return;
    const heading = document.querySelector(".swap");
    if (!heading)
        return;
    const phrases = heading.querySelectorAll(".phrase");
    const first = phrases[0];
    const second = phrases[1];
    if (!first || !second || phrases.length !== 2)
        return;
    const apart = second.offsetTop - first.offsetTop;
    // Stacked by a stylesheet that has not loaded, or laid out side by
    // side by some future change: either way there is no vertical journey
    // to make, and a swap of nothing is worse than none.
    if (apart <= 0)
        return;
    /* How deep the C's stroke goes.
     *
     * MEASURED TWICE, because two different things limit it. Against the
     * travel, so the letter keeps its proportions at every width — a C is
     * about three-quarters as wide as it is tall. And against the room
     * actually to the left of the heading, because the page clips at its
     * edge: at 390px the heading begins 14px in, so an arc drawn to a
     * letter's proportions would take the first characters off the side
     * of the page mid-sweep. Where there is room it is a letter; where
     * there is not it is as much of one as fits.
     *
     * The two phrases take arcs of DIFFERENT depth, and that difference
     * is the only thing keeping them apart. They cross at the half-way
     * point, where both are at the same height, so the gap between them
     * there is exactly the difference between the two depths.
     *
     * Not a stagger — that cannot work, and the arithmetic says so before
     * any of it is built. The bow is sin(pi * p), symmetric about the
     * middle, so wherever a delay makes their heights equal it makes
     * their sideways offsets equal too: they would meet exactly, later. */
    /* The room is measured from the TEXT, not from the block that holds
     * it. The heading is centred, so the block reaches the gutter while
     * the glyphs start well inside it — measuring the block gave 23px at
     * 390px where the letters really had 36px, and the arc came out a
     * third shallower than it needed to be. A Range over the contents
     * reports where the ink actually is. */
    const ink = document.createRange();
    ink.selectNodeContents(first);
    const inked = ink.getBoundingClientRect();
    const edge = inked.width > 0 ? inked.left : first.getBoundingClientRect().left;
    const room = edge - 4;
    const bow = Math.max(0, Math.min(apart * 0.72, room));
    first.style.setProperty("--from-y", `${apart}px`);
    first.style.setProperty("--bow", `${bow}px`);
    second.style.setProperty("--from-y", `${-apart}px`);
    second.style.setProperty("--bow", `${bow * 0.42}px`);
    /* Where they wait until the section is reached. The animation's own
     * first frame is this same position, so nothing jumps when it
     * starts. */
    first.style.transform = `translateY(${apart}px)`;
    second.style.transform = `translateY(${-apart}px)`;
    const seen = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (!entry.isIntersecting)
                continue;
            seen.unobserve(entry.target);
            /* The animation carries the whole journey now, so there is no
             * second write to transition FROM and no layout to force:
             * adding the class starts it, and its own first frame is where
             * the phrases already are. */
            heading.classList.add("swapping");
            // Take the animation away once it has been spent, so nothing
            // that moves these phrases later — a resize, a late font —
            // animates them again. The brief asked for once. The waiting
            // transform goes in the same breath, so there is no frame
            // between losing the animation and losing the offset.
            window.setTimeout(() => {
                first.style.transform = "";
                second.style.transform = "";
                heading.classList.remove("swapping");
            }, SWAP_DONE_MS);
        }
    }, { threshold: 0.6 });
    seen.observe(heading);
}
/* ---- the carousel, closed ---------------------------------------------
 * The carousel opens full screen and `<details>` does all of it: the
 * summary opens it, the summary closes it, and with no script at all it
 * opens inline instead. These are the two things a summary cannot know.
 *
 * ESCAPE. Anything covering the screen has to answer Escape — a reader
 * whose way out is a word in a corner has been given a puzzle.
 *
 * THE BACKDROP. A photograph does not fill the sheet, so there is
 * always ground around it, and clicking the ground means "I am done".
 * Only the ground: a click that lands on a photograph is someone
 * looking at it, not someone leaving.
 */
function closeTheCarousel() {
    /* INNERMOST FIRST. Two things can be open at once now — a group at
     * the front, and one project's carousel on top of it — and Escape
     * must take the top one off rather than both. Closing the group
     * while its carousel is up would drop the reader two levels for one
     * keystroke. */
    const innermost = () => document.querySelector(".shots[open]")
        ?? document.querySelector(".group[open]")
        /* A dossier is a third thing that can be over the page. It is never
         * open at the same time as the gallery — they are different
         * sections — so it only has to be in the list, not ordered against
         * the other two. */
        ?? document.querySelector(".dossier[open]");
    const shut = (box) => {
        if (!box)
            return;
        box.open = false;
        // The summary that opened it takes the focus back, or the keyboard
        // is left standing on an element no longer on the screen.
        box.querySelector("summary")?.focus();
    };
    addEventListener("keydown", (ev) => {
        if (ev.key !== "Escape")
            return;
        shut(innermost());
    });
    /* CLOSING A GROUP PUTS ITS PROJECTS BACK.
     *
     * <details> remembers. Open a project's carousel, close the group
     * around it, and the project stays open — so the next visit to that
     * reference lands straight in the carousel, past the patchwork the
     * reader was going back for. Reported from the page: "i get back at
     * ref4 and i end up directly at the carrousel".
     *
     * `toggle` rather than a click handler, so it holds however the
     * group was closed: its own summary, Escape, or the ground. */
    for (const group of document.querySelectorAll(".group")) {
        group.addEventListener("toggle", () => {
            if (group.open)
                return;
            for (const shots of group.querySelectorAll(".shots[open]")) {
                shots.open = false;
            }
        });
    }
    /* THE GROUND IS THE WAY OUT, at both levels.
     *
     * There is no close button any more. A photograph never fills the
     * sheet, so there is always ground around it, and clicking the
     * ground means "I am done" — one level at a time, so a carousel
     * closes back to the group it came from rather than all the way out.
     *
     * ONLY the ground: a click that lands on a photograph is someone
     * looking at it, and a click on one of the prints in the group is
     * someone opening it, which <details> handles by itself. */
    for (const reel of document.querySelectorAll(".reel")) {
        reel.addEventListener("click", (ev) => {
            if (ev.target !== reel)
                return;
            shut(reel.closest("details"));
        });
    }
    for (const front of document.querySelectorAll(".group-front")) {
        front.addEventListener("click", (ev) => {
            // The group's own box and nothing inside it. `.fridge` holds the
            // prints, and each print is a summary that opens its carousel.
            if (ev.target !== front)
                return;
            shut(front.closest("details"));
        });
    }
    /* The same way out of a document. The pages are narrower than the
     * sheet, so there is always margin to click — and a click ON a page
     * is someone reading it, which must do nothing at all. */
    for (const leaves of document.querySelectorAll(".leaves")) {
        leaves.addEventListener("click", (ev) => {
            if (ev.target !== leaves)
                return;
            shut(leaves.closest("details"));
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
/* ---- going into the work changes the light ---------------------------
 *
 * "By default we are cream, always. Scrolling does nothing. If the user
 *  clicks on Explore selected work we move to the right section and we
 *  switch to the grey palette. Re-clicking does nothing. If we quit and
 *  come back we are cream again."
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
const TINT_MS = 700;
function tintOnTheWayIn() {
    for (const trigger of document.querySelectorAll("[data-tint]")) {
        trigger.addEventListener("click", () => {
            const want = trigger.dataset["tint"];
            if (!want || document.documentElement.dataset["palette"] === want)
                return;
            if (!reduced) {
                document.documentElement.classList.add("tinting");
                window.setTimeout(() => document.documentElement.classList.remove("tinting"), TINT_MS);
            }
            document.documentElement.dataset["palette"] = want;
        });
    }
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
/* ---- the field holds still while the page is moving --------------------
 *
 * "When we stop the scroll they should move, and stop when the
 *  scrolling goes back."
 *
 * The drift is not scroll-driven and never was — it keeps its own clock.
 * This only decides WHEN that clock runs. Two reasons it is worth
 * having: motion that competes with a scroll is motion nobody can
 * follow, and the compositor has one less thing to carry at the moment
 * it is busiest.
 *
 * `animation-play-state` rather than anything of our own, so the words
 * resume exactly where they were rather than restarting their lap.
 *
 * The window's scroll, not an observer: an IntersectionObserver reports
 * where things are, and the question here is only whether the page is
 * moving at all.
 */
const SETTLED_MS = 160; // long enough to bridge the gaps between events
function stillWhileScrolling() {
    const cloud = document.querySelector(".cloud");
    if (!cloud)
        return;
    let settling = 0;
    addEventListener("scroll", () => {
        cloud.classList.add("held");
        window.clearTimeout(settling);
        settling = window.setTimeout(() => cloud.classList.remove("held"), SETTLED_MS);
    }, { passive: true });
}
function startMotion() {
    releaseHeadlines();
    observeReveals();
    stillWhileScrolling();
}
if (!reduced)
    prepareMotion();
syncBar();
WIDE.addEventListener("change", syncBar);
markCurrentSection();
closeMenuOnNavigate();
copyButtons();
tintOnTheWayIn();
countTheWait();
softWhileMoving();
exchangePhrases();
closeTheCarousel();
keepOneAddress();
photographsDrift();
showTheRelease();
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
function show() {
    // STILL THE ONLY PLACE THE PAGE IS SHOWN. The wait is in front of the
    // one reveal, not a second way of reaching it.
    const owed = Math.max(0, COVER_FLOOR_MS - performance.now());
    window.setTimeout(() => {
        reveal();
        if (!reduced)
            startMotion();
    }, owed);
}
if (document.readyState === "complete")
    show();
else
    window.addEventListener("load", show, { once: true });
//# sourceMappingURL=landing.js.map