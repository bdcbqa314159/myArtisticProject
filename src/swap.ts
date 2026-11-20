/* The two phrases exchange places — once per arrival, not once ever.
 *
 * "Independent by design. Collaborative by nature." The brief asked for
 * the exchange to be triggered "une seule fois à l'apparition de la
 * section, sans boucle" — once on the section's appearance, with no
 * loop. It was read as once per PAGE, and the observer unobserved after
 * the first crossing. Watched on the page that is the same complaint
 * the reveals had: alive the first time, dead on the way back.
 *
 * It still does not loop. It plays once each time the section arrives,
 * and nothing moves while the reader is there.
 *
 * WHY THIS IS A MODULE. The sequence has a timer in it, and the thing
 * that can silently break is what happens when the reader leaves
 * MID-FLIGHT: the settle timer has to be cancelled and the phrases put
 * back where the animation begins, or the next arrival finds them
 * already in place and plays nothing. That cannot be observed in the
 * browser this repository drives — an IntersectionObserver callback
 * needs a rendering opportunity and the page is driven inside an
 * iframe, which gets none — so the sequence is written here with the
 * page passed in, and `tools/swap-check.mjs` passes a fake one.
 */

/** Everything the sequence needs from the page it is animating. */
export interface Stage {
  /** Put the phrases where the animation's first frame is. */
  park(): void;
  /** Start it. */
  play(): void;
  /** Take the animation off, leaving whatever is underneath. */
  stop(): void;
  /** Leave them where they belong, with nothing on them at all. */
  rest(): void;
  after(ms: number, run: () => void): number;
  cancel(timer: number): void;
}

/** A function to call with `true` when the section arrives and `false`
 *  when it has entirely gone. */
export function swapOnArrival(
  stage: Stage,
  settleMs: number,
): (arriving: boolean) => void {
  let settling = 0;

  return (arriving: boolean): void => {
    // Whatever was pending belongs to the last arrival.
    stage.cancel(settling);

    if (!arriving) {
      /* Off the screen: take the animation away and park them again.
       * Both, and in this order — a heading left mid-animation with no
       * offset under it would arrive next time already in place, and
       * the exchange would not be seen at all. */
      stage.stop();
      stage.park();
      return;
    }

    stage.park();
    stage.play();

    /* Spent. The offset goes in the same breath as the animation, so
     * there is no frame between losing the one and losing the other —
     * and with both gone, anything that moves these phrases later (a
     * resize, a late font) does not animate them. */
    settling = stage.after(settleMs, () => {
      stage.rest();
      stage.stop();
    });
  };
}
