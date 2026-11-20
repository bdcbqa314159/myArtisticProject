/* Marked while in view, unmarked once entirely out of it.
 *
 * Both of the page's reveals work this way — the blocks that fade and
 * rise, and the headlines released word by word — and both used to do
 * it ONCE: the observer unobserved on the first crossing, on the
 * grounds that re-animating on the way back up reads as a glitch.
 * Watched on the page it reads as the opposite: a section that was
 * alive the first time and dead every time after. "The title stays in
 * place and no animation."
 *
 * Separated out for the reason `cover.ts` and `scroll.ts` were: the
 * thing worth checking is the wiring, and it cannot be checked in a
 * browser here. IntersectionObserver callbacks arrive on a rendering
 * opportunity, and this harness runs a page in an iframe, where there
 * are none — measured: scrolling four thousand pixels down and back
 * left every one of the twenty-eight blocks exactly as it was. So the
 * wiring is a function with the observer passed in, and
 * `tools/arrive-check.mjs` passes a fake one and checks what happens.
 */

/** As much of an IntersectionObserverEntry as this needs. */
export interface Seen {
  readonly target: Element;
  readonly isIntersecting: boolean;
}

/** As much of an IntersectionObserver as this needs. Deliberately no
 *  `unobserve`: nothing here stops watching, and a type that cannot
 *  express it cannot regress to it. */
export interface Watcher {
  observe(el: Element): void;
}

export type Make = (
  callback: (entries: Seen[]) => void,
  options: { rootMargin?: string; threshold?: number },
) => Watcher;

/** Watch `blocks`, marking each while it is in view.
 *
 *  TWO OBSERVERS, WITH DIFFERENT MARGINS, which is the whole point.
 *
 *  Arriving fires early — `margin` shaves a slice off the bottom of the
 *  root so the motion finishes about where the eye lands rather than
 *  after it. Leaving must NOT use that margin: with the bottom of the
 *  root pulled up, a block being scrolled back towards from below stops
 *  intersecting while it is still visibly on screen, and the words
 *  would retract in front of the reader. So the reset watches the
 *  viewport exactly, and happens only once the block is entirely out of
 *  sight — where it costs nothing and nobody sees it.
 */
export function whileInView(
  blocks: Iterable<Element>,
  make: Make,
  mark: (el: Element, on: boolean) => void,
  margin = "0px 0px -12% 0px",
  threshold = 0.01,
): void {
  const arriving = make((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) mark(entry.target, true);
    }
  }, { rootMargin: margin, threshold });

  const leaving = make((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) mark(entry.target, false);
    }
  }, { threshold: 0 });

  for (const el of blocks) {
    arriving.observe(el);
    leaving.observe(el);
  }
}
