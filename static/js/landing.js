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
 * One observer for the whole page. `once` is deliberate: a block that has
 * arrived stays arrived, because re-animating on the way back up reads as
 * a glitch rather than as an effect.
 */
function revealOnScroll() {
    const blocks = document.querySelectorAll("section > .wrap > *");
    for (const el of blocks)
        el.classList.add("reveal");
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
        if (h.tagName === "H1") {
            // The hero headline is above the fold by definition, so it is
            // released on the next frame rather than waiting for an observer.
            //
            // This is not a micro-optimisation. On a cold Safari launch the
            // page can still be hidden when the observer would have run, and
            // callbacks are deferred until it is visible — which showed up as
            // a blank headline for the first seconds. A portfolio handed to
            // someone on a phone cannot open on an empty hero.
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
    // observers, no headline stays invisible. Four seconds is long past
    // any legitimate reveal and still inside the time someone is looking.
    setTimeout(() => {
        for (const h of document.querySelectorAll(".split"))
            h.classList.add("in");
        for (const el of document.querySelectorAll(".reveal"))
            el.classList.add("in");
    }, 4000);
}
/* Near-neutral, and cold.
 *
 * This used to be hues 18, 44 and 352 at 85% saturation — orange, amber
 * and red — which is where the warmth in the hero was actually coming
 * from. It is painted on a canvas, so no amount of editing the
 * stylesheet could reach it, and the palette looked unchanged.
 *
 * Now the same family as the rest of the page: hues either side of 240
 * at a saturation low enough that it reads as a shift in the grey
 * rather than as a colour. See the palette note in site.css. */
const WASH_SATURATION = 26;
const WASH = [
    { hue: 232, radius: 0.75, orbit: 0.18, speed: 0.013, phase: 0.0 },
    { hue: 248, radius: 0.60, orbit: 0.24, speed: 0.019, phase: 1.7 },
    { hue: 214, radius: 0.65, orbit: 0.21, speed: 0.011, phase: 3.4 },
    { hue: 260, radius: 0.55, orbit: 0.27, speed: 0.023, phase: 5.1 },
];
function heroWash(canvas) {
    const ctx2d = canvas.getContext("2d", { alpha: true });
    if (!ctx2d)
        return;
    const ctx = ctx2d;
    let w = 0;
    let h = 0;
    function resize() {
        // Cap the device pixel ratio at 2. Beyond that it is four gradients
        // over four times the pixels for a difference nobody can see in a
        // blurred backdrop.
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const rect = canvas.getBoundingClientRect();
        w = Math.max(1, Math.round(rect.width * dpr));
        h = Math.max(1, Math.round(rect.height * dpr));
        canvas.width = w;
        canvas.height = h;
    }
    function draw(t) {
        const short = Math.min(w, h);
        ctx.clearRect(0, 0, w, h);
        ctx.globalCompositeOperation = "lighter";
        for (const b of WASH) {
            const a = t * b.speed * Math.PI * 2 + b.phase;
            const cx = w / 2 + Math.cos(a) * b.orbit * short;
            const cy = h / 2 + Math.sin(a * 0.8) * b.orbit * short;
            const r = b.radius * short;
            const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
            g.addColorStop(0, `hsl(${b.hue} ${WASH_SATURATION}% 58% / 0.42)`);
            g.addColorStop(0.55, `hsl(${b.hue} ${WASH_SATURATION}% 54% / 0.14)`);
            g.addColorStop(1, `hsl(${b.hue} ${WASH_SATURATION}% 50% / 0)`);
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    resize();
    new ResizeObserver(() => {
        resize();
        if (reduced)
            draw(0);
    }).observe(canvas);
    // Asked for less motion: paint one frame and stop. The hero keeps its
    // colour, nothing moves, and no animation frame is ever requested.
    if (reduced) {
        draw(0);
        return;
    }
    let frame = 0;
    let running = false;
    let start = 0;
    function tick(now) {
        if (!running)
            return;
        if (!start)
            start = now;
        draw((now - start) / 1000);
        frame = requestAnimationFrame(tick);
    }
    function run(on) {
        if (on === running)
            return;
        running = on;
        if (on)
            frame = requestAnimationFrame(tick);
        else
            cancelAnimationFrame(frame);
    }
    // Off when scrolled past, and off in a background tab. A decorative
    // backdrop nobody is looking at should not cost anyone battery.
    new IntersectionObserver((entries) => {
        for (const e of entries)
            run(e.isIntersecting && !document.hidden);
    }, { threshold: 0 }).observe(canvas);
    document.addEventListener("visibilitychange", () => {
        run(!document.hidden && canvas.getBoundingClientRect().bottom > 0);
    });
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
        if (ev.target.closest(".menu-items a"))
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
/* ---- uncovering the page ---------------------------------------------
 * `load` rather than `DOMContentLoaded`: the point is to wait for the
 * photographs, not merely for the markup. With no lazy attribute left on
 * them they are all in flight from the start, so this is the moment the
 * page is genuinely whole.
 *
 * Capped, because "whole" is not worth any amount of waiting. One slow
 * image on a venue's network must not hold the rest hostage — past the
 * cap the page is shown and the stragglers arrive into it, which is the
 * ordinary behaviour we were avoiding, not a broken one.
 */
const UNCOVER_CAP_MS = 2600;
let uncovered = false;
function uncover() {
    // Both the load event and the cap can call this; the second call must
    // not replay the motion.
    if (uncovered)
        return;
    uncovered = true;
    document.documentElement.classList.remove("booting");
    // Started here, not at parse time. Observers fire on what is in the
    // viewport whether or not anyone can see it, so motion set up behind
    // the cover would have finished playing by the time the cover lifted —
    // the reveal would exist and never be seen.
    if (!reduced) {
        splitHeadlines();
        revealOnScroll();
    }
}
if (document.readyState === "complete") {
    uncover();
}
else {
    window.addEventListener("load", uncover, { once: true });
    setTimeout(uncover, UNCOVER_CAP_MS);
}
closeMenuOnNavigate();
copyButtons();
const wash = document.querySelector(".hero-wash");
if (wash)
    heroWash(wash);
//# sourceMappingURL=landing.js.map