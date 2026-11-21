/* Getting around the page, and the chrome that says where you are.
 *
 * The bar and its menu, the marker that follows the reader down the
 * sections, every in-page link, the crossing that takes them there —
 * blur, move, clear — and the light changing the first time someone
 * leaves the top of the page.
 */
import { reduced } from "./reduced.js";
export const WIDE = matchMedia("(min-width: 50rem)");
export function syncBar() {
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
export function markCurrentSection() {
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
export function closeMenuOnNavigate() {
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
export const PRESS_MS = 140;
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
export function crossTo(top, onDone) {
    const root = document.documentElement;
    // Nothing to hide behind: go straight there.
    if (reduced) {
        window.scrollTo({ top, behavior: "instant" });
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
export function keepOneAddress() {
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
                /* EVERY REDIRECTION CROSSES. The band did and the buttons
                 * travelled — an eased journey of up to 1100ms — so the same
                 * destination moved two different ways depending on which
                 * element had been pressed: the logo rewound the whole page
                 * from the foot of it, while the menu went there at once.
                 *
                 * Settled with the client: one motion for anything that takes
                 * the reader somewhere. The travel is removed rather than left
                 * unused — it is in the history if it is ever wanted back.
                 *
                 * The band stops guessing where the reader is the moment the
                 * crossing ends. */
                crossTo(landing, () => marker?.release(id));
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
 * ONCE PER ARRIVAL, and that is not the same as once per page — which
 * is how "une seule fois … sans boucle" was read, and how it was built.
 * It still does not loop: nothing moves while the reader is in the
 * section. It plays when the section arrives, every time it arrives,
 * like the reveals. `swap.ts` sequences it; `tools/swap-check.mjs`
 * holds the interrupted case, which is the one that breaks quietly.
 */
const TINT_MS = 700;
export function tintOnTheWayIn() {
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
//# sourceMappingURL=nav.js.map