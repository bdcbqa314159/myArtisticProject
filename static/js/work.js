/* The gallery: a reference opened, a project opened inside it.
 *
 * Closing at the right level, the band at the edge that takes the
 * reader back out, the light that says a print opens, and swapping in
 * the bigger copy of a photograph once it is actually being looked at.
 */
import { PHOTOGRAPHS } from "./photographs.js";
import { horizonFor } from "./horizon.js";
export function sharpenOnOpen() {
    const upgrade = (root, which) => {
        for (const el of root.querySelectorAll(which)) {
            const big = el.dataset["big"];
            const img = el instanceof HTMLImageElement
                ? el
                : el.querySelector("img");
            if (!big || !img)
                continue;
            /* Through the queue, so it is one fetch and not two if the
             * warming had already reached it — and urgent, because the
             * reader is looking at this one. */
            PHOTOGRAPHS.urgent([big]);
            const bigger = new Image();
            bigger.decoding = "async";
            bigger.addEventListener("load", () => {
                img.src = big;
                delete el.dataset["big"];
            });
            bigger.src = big;
        }
    };
    /* WHAT IS ACTUALLY BEING LOOKED AT, AND NOTHING ELSE.
     *
     * A reference holds five prints, and each print holds a carousel of
     * photographs — so "everything inside the group" would fetch about
     * five megabytes the moment a reference opened, most of it for
     * projects the reader has not touched. Measured across the fixture:
     * 126 big copies, 16.4MB in total.
     *
     * So opening a reference takes the five prints, and opening a project
     * takes that project's photographs. */
    for (const group of document.querySelectorAll(".group")) {
        group.addEventListener("toggle", () => {
            if (!group.open)
                return;
            /* WHERE THE PAGE IS, SO THE FRONT CAN JOIN IT.
             *
             * Measured on the phone that has the fault: the page is told its
             * viewport is 641px tall — `innerHeight` and `clientHeight` agree
             * and the difference between them is zero — while the screen
             * plainly shows content below that line, under the floating
             * toolbar. Safari paints a strip it never told the page about,
             * and the page's own scrolling content is drawn into it. That is
             * why the site looks continuous under the bar.
             *
             * A `position: fixed` element is not drawn there. It is pinned to
             * the 641 the page was given, so it stops exactly at the top of
             * that strip and the page shows beneath it. No height can reach
             * past the end of the world the element was handed — seven
             * attempts at bigger numbers proved that the slow way.
             *
             * So the front stops being fixed and becomes ordinary document
             * content, parked at the scroll position. Scrolling is frozen
             * while a patchwork is open, so it does not move; and because it
             * is now part of the page, it is painted into the same strip the
             * page is.
             */
            const where = `${Math.round(window.scrollY)}px`;
            document.documentElement.style.setProperty("--open-at", where);
            upgrade(group, "summary[data-big]");
        });
    }
    for (const shots of document.querySelectorAll(".shots")) {
        shots.addEventListener("toggle", () => {
            if (!shots.open)
                return;
            /* The project's own photographs, before whatever the warming was
             * working through. The small copies as well as the big ones: the
             * reader may see either, depending on which arrives first. */
            PHOTOGRAPHS.urgent([...shots.querySelectorAll("img")]
                .flatMap((img) => [img.currentSrc || img.src, img.dataset["big"] || ""]));
            upgrade(shots, "img[data-big]");
        });
    }
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
export function closeTheCarousel() {
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
    /* AND A PROJECT REOPENED STARTS AT ITS FIRST PHOTOGRAPH.
     *
     * The strip is a scroll container, and a scroll container remembers.
     * Reported from the page: go through a project's photographs to the
     * third, leave, wander the page, come back to the same project — and
     * it opens on the third. The <details> had been put back; the scroll
     * inside it had not.
     *
     * Reset when it CLOSES rather than when it opens: on the way in the
     * strip is already on screen, and moving it there would be a jump the
     * reader watches. */
    for (const shots of document.querySelectorAll(".shots")) {
        shots.addEventListener("toggle", () => {
            if (shots.open)
                return;
            const reel = shots.querySelector(".reel");
            if (reel)
                reel.scrollLeft = 0;
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
        /* A BAND AT THE EDGE, 44px of it.
         *
         * The ground around the prints was already the way back, and on a
         * phone there was 23px of it — a sliver at the edge of the screen,
         * where a miss lands on a print and opens its carousel. This is
         * the same way out, made the size of a thumb: a ring drawn with a
         * clip-path, so the middle still belongs to the prints.
         *
         * Added here rather than in the markup because it is an
         * affordance for the version of this gallery that has script. With
         * none, the focus is in the page rather than over it and the way
         * out is the page itself. */
        const out = document.createElement("i");
        out.className = "way-out";
        out.setAttribute("aria-hidden", "true");
        front.prepend(out);
        front.addEventListener("click", (ev) => {
            // The group's own box, or the band: both mean "I am done".
            // `.fridge` holds the prints, and each print is a summary that
            // opens its carousel, so nothing else here closes anything.
            if (ev.target !== front && ev.target !== out)
                return;
            /* Innermost, like Escape. The band sits under the carousel, so
             * while a project is open it cannot be clicked at all — but if
             * that ever changes, one keystroke and one click should take the
             * same thing off. */
            shut(innermost());
        });
    }
    /* AND THE FOCUS HAS TO COVER THE SCREEN WHEN IT OPENS.
     *
     * `.group-front` is `position: fixed; inset: 0`, which resolves
     * against the nearest ancestor with a transform — and every section
     * is inside a `.reveal` block that carries `translateY` until its
     * `.in` arrives. Measured: a group opened before that put the focus
     * inside the section at 343x3055 instead of over the 390x900 screen.
     *
     * `.reveal.in` sets `transform: none`, so making sure the block is
     * revealed before the focus opens is the whole fix. It is also the
     * third time this page has met the containing-block rule; the other
     * two are written up in site.css. */
    for (const group of document.querySelectorAll(".group")) {
        group.addEventListener("toggle", () => {
            if (group.open)
                group.closest(".reveal")?.classList.add("in");
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
export function placeTheLights() {
    for (const light of document.querySelectorAll("[data-look]")) {
        const spot = (light.dataset["look"] || "").trim().split(/\s+/);
        if (spot.length !== 2)
            continue;
        const [x, y] = spot.map(Number);
        if (!Number.isFinite(x) || !Number.isFinite(y))
            continue;
        light.style.setProperty("--look-x", `${x}%`);
        light.style.setProperty("--look-y", `${y}%`);
    }
}
/* ---- one horizon for a project's photographs -------------------------
 * On a wide screen the slide is short and wide, so its height binds
 * every photograph and they already share one. On a phone the slide is
 * tall and narrow, the WIDTH binds instead, and an upright photograph
 * came out twice the height of a landscape one — the same rule, and on
 * that screen it reads as an accident.
 *
 * So the height is chosen: the tallest they can all be while the widest
 * of them still fits. `horizon.ts` does the arithmetic.
 *
 * MEASURED FROM THE MARKUP, not from the pixels. Every photograph
 * carries `width` and `height` attributes, so the shapes are known
 * before anything has loaded and the horizon does not change under the
 * reader when a file arrives. `naturalWidth` is the fallback for
 * anything that lost its attributes.
 */
export function levelTheCarousels() {
    const settle = (shots) => {
        const reel = shots.querySelector(".reel");
        if (!reel)
            return;
        const photographs = [...reel.querySelectorAll("img")];
        if (!photographs.length)
            return;
        const aspects = photographs.map((img) => {
            const wide = Number(img.getAttribute("width")) || img.naturalWidth;
            const tall = Number(img.getAttribute("height")) || img.naturalHeight;
            return tall > 0 ? wide / tall : 0;
        });
        /* The shortest photograph's own pixels: the horizon may not go
         * above it, or that one is stretched to meet the others. Read from
         * the file where it has arrived and from the markup where it has
         * not — the two agree in shape, and the attributes are there from
         * the first paint. */
        const pixels = photographs.map((img) => 
        /* THE BIG COPY'S HEIGHT, which is what will be on screen once it
         * has arrived. `naturalHeight` here is whatever has loaded so
         * far — at the moment a project opens that is the small copy, and
         * using it capped the horizon at the small copy's height for
         * good: measured, 398x266 photographs in an 801px slide on a
         * 1400px screen. The template says the big copy's height because
         * the build is the only place that knows it without waiting. */
        Number(img.dataset["bigH"])
            || img.naturalHeight
            || Number(img.getAttribute("height"))
            || 0)
            .filter((h) => h > 0);
        const slide = reel.querySelector(".slide");
        const box = (slide ?? reel).getBoundingClientRect();
        const horizon = horizonFor(aspects, box.width, box.height, pixels.length ? Math.min(...pixels) : Infinity);
        reel.style.setProperty("--horizon", `${Math.round(horizon)}px`);
    };
    for (const shots of document.querySelectorAll(".shots")) {
        shots.addEventListener("toggle", () => {
            if (shots.open)
                settle(shots);
        });
    }
    /* And again when the screen changes shape, because the horizon is a
     * measurement of it: a phone turned on its side is a different slide
     * and a different answer. */
    addEventListener("resize", () => {
        for (const shots of document.querySelectorAll(".shots[open]")) {
            settle(shots);
        }
    }, { passive: true });
}
//# sourceMappingURL=work.js.map