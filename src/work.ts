/* The gallery: a reference opened, a project opened inside it.
 *
 * Closing at the right level, the band at the edge that takes the
 * reader back out, the light that says a print opens, and swapping in
 * the bigger copy of a photograph once it is actually being looked at.
 */

import { PHOTOGRAPHS } from "./photographs.js";

export function sharpenOnOpen(): void {
  const upgrade = (root: ParentNode, which: string): void => {
    for (const el of root.querySelectorAll<HTMLElement>(which)) {
      const big = el.dataset["big"];
      const img = el instanceof HTMLImageElement
        ? el
        : el.querySelector<HTMLImageElement>("img");
      if (!big || !img) continue;

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
  for (const group of document.querySelectorAll<HTMLDetailsElement>(".group")) {
    group.addEventListener("toggle", () => {
      if (group.open) upgrade(group, "summary[data-big]");
    });
  }
  for (const shots of document.querySelectorAll<HTMLDetailsElement>(".shots")) {
    shots.addEventListener("toggle", () => {
      if (!shots.open) return;
      /* The project's own photographs, before whatever the warming was
       * working through. The small copies as well as the big ones: the
       * reader may see either, depending on which arrives first. */
      PHOTOGRAPHS.urgent(
        [...shots.querySelectorAll<HTMLImageElement>("img")]
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
export function closeTheCarousel(): void {
  /* INNERMOST FIRST. Two things can be open at once now — a group at
   * the front, and one project's carousel on top of it — and Escape
   * must take the top one off rather than both. Closing the group
   * while its carousel is up would drop the reader two levels for one
   * keystroke. */
  const innermost = (): HTMLDetailsElement | null =>
    document.querySelector<HTMLDetailsElement>(".shots[open]")
    ?? document.querySelector<HTMLDetailsElement>(".group[open]")
    /* A dossier is a third thing that can be over the page. It is never
     * open at the same time as the gallery — they are different
     * sections — so it only has to be in the list, not ordered against
     * the other two. */
    ?? document.querySelector<HTMLDetailsElement>(".dossier[open]");

  const shut = (box: HTMLDetailsElement | null): void => {
    if (!box) return;
    box.open = false;
    // The summary that opened it takes the focus back, or the keyboard
    // is left standing on an element no longer on the screen.
    box.querySelector("summary")?.focus();
  };

  addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
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
  for (const group of document.querySelectorAll<HTMLDetailsElement>(".group")) {
    group.addEventListener("toggle", () => {
      if (group.open) return;
      for (const shots of group.querySelectorAll<HTMLDetailsElement>(".shots[open]")) {
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
  for (const shots of document.querySelectorAll<HTMLDetailsElement>(".shots")) {
    shots.addEventListener("toggle", () => {
      if (shots.open) return;
      const reel = shots.querySelector<HTMLElement>(".reel");
      if (reel) reel.scrollLeft = 0;
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
  for (const reel of document.querySelectorAll<HTMLElement>(".reel")) {
    reel.addEventListener("click", (ev) => {
      if (ev.target !== reel) return;
      shut(reel.closest("details"));
    });
  }

  for (const front of document.querySelectorAll<HTMLElement>(".group-front")) {
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
      if (ev.target !== front && ev.target !== out) return;
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
  for (const group of document.querySelectorAll<HTMLDetailsElement>(".group")) {
    group.addEventListener("toggle", () => {
      if (group.open) group.closest(".reveal")?.classList.add("in");
    });
  }

  /* The same way out of a document. The pages are narrower than the
   * sheet, so there is always margin to click — and a click ON a page
   * is someone reading it, which must do nothing at all. */
  for (const leaves of document.querySelectorAll<HTMLElement>(".leaves")) {
    leaves.addEventListener("click", (ev) => {
      if (ev.target !== leaves) return;
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
export function placeTheLights(): void {
  for (const light of document.querySelectorAll<HTMLElement>("[data-look]")) {
    const spot = (light.dataset["look"] || "").trim().split(/\s+/);
    if (spot.length !== 2) continue;
    const [x, y] = spot.map(Number);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    light.style.setProperty("--look-x", `${x}%`);
    light.style.setProperty("--look-y", `${y}%`);
  }
}
