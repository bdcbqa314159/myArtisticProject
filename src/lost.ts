/* An image that did not arrive.
 *
 * THE COMPLAINT. Landing on the deployed site with a cleaned cache and
 * finding torn-page icons where the photographs should be. Measured
 * first, because the two states look nothing alike in the code and
 * identical in a complaint:
 *
 *   - an image STILL LOADING draws nothing at all. No glyph, no text,
 *     an empty box. Slowness is not what was being seen.
 *   - an image that FAILED draws the browser's broken-image glyph and,
 *     beside it, the whole `alt` attribute. 163 of this page's images
 *     carry a full sentence there, so a handful of failures reads as a
 *     page that is broken rather than a page that is loading.
 *
 * And every one of the deployed site's 266 images answers a request
 * correctly, fetched twelve at a time — so nothing is missing. What
 * fails is the landing itself: a cold cache asks for 167 images from
 * the document while the warming queue asks for the rest, and a phone
 * under that pressure drops some. Nothing in the page ever asked again,
 * so one dropped image stayed torn for the whole visit.
 *
 * THIS IS THE ASKING AGAIN. It is deliberately not the queue in
 * `preload.ts`: that one decides what to fetch BEFORE anyone needs it,
 * and this one is about an <img> already on the page that the reader
 * can see has failed. Different question, different lifetime, different
 * failure.
 *
 * The policy lives here, with the clock passed in, so it can be driven
 * exactly in `tools/lost-check.mjs` rather than waited for in a browser.
 */

/** What this needs from the page. */
export interface Again {
  /** Try this one again, in `wait` milliseconds. */
  retry(key: string, wait: number): void;
  /** It is not coming. Leave the box quiet. */
  giveUp(key: string): void;
}

export interface Recovery {
  /** An image failed. True if it will be tried again. */
  failed(key: string): boolean;
  /** It arrived — forget what went before, so a later failure is fresh. */
  arrived(key: string): void;
  /** How many times this one has failed. */
  tries(key: string): number;
}

/** Ask again, twice, with the second wait longer than the first.
 *
 *  TWICE, NOT UNTIL IT WORKS. A retry that never stops is a page that
 *  hammers a server which has already said no, from a phone that is
 *  already struggling — and the reader has long since scrolled past.
 *  Two is enough for the case this is for, which is a request dropped
 *  in a crowd rather than a file that is not there.
 */
export function recovering(
  again: Again,
  max = 2,
  first = 900,
): Recovery {
  const failures = new Map<string, number>();

  return {
    failed(key: string): boolean {
      const n = (failures.get(key) ?? 0) + 1;
      failures.set(key, n);
      if (n > max) {
        again.giveUp(key);
        return false;
      }
      /* Longer each time: a crowd that has not cleared in 900ms is
       * unlikely to have cleared by 1800ms either, and the second ask
       * costs nothing to postpone. */
      again.retry(key, first * n);
      return true;
    },

    arrived(key: string): void {
      failures.delete(key);
    },

    tries(key: string): number {
      return failures.get(key) ?? 0;
    },
  };
}
