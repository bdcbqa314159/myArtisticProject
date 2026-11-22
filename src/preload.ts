/* Warming the photographs before they are looked at.
 *
 * THE PROBLEM, MEASURED. Seventeen images block the cover — 0.4MB, the
 * first screen. The other hundred and fifty are `loading="lazy"`, 7.6MB
 * of them, and they arrive when the reader reaches them: a section
 * assembles itself in front of whoever scrolled to it. On top of that
 * sit 132 bigger copies, fetched when a reference or a project opens.
 *
 * The cover cannot fix this. Holding the page until all of it has
 * arrived would mean 16MB before the first word, which is the other
 * way to ruin it. So the page opens on its first screen, as now, and
 * everything else is fetched QUIETLY, in reading order, before anyone
 * gets there.
 *
 * THE SHAPE OF IT
 *
 *   state   url -> queued | loading | done | failed, so nothing is
 *           ever fetched twice and the caller can ask what is ready.
 *   lanes   three tiers of work, picked lowest-first: 0 is what is
 *           open NOW, 1 is what is probably next, 2 is the rest of the
 *           page. A tier is a plain array used as a queue — the work is
 *           always appended and always taken from the front, and with a
 *           few hundred items that is the right structure and a heap is
 *           not.
 *   running how many fetches are in flight, held under `width` so the
 *           warming never competes with what the reader asked for.
 *
 * `urgent` pushes into tier 0 and pumps immediately; `warm` pushes into
 * tier 2 and pumps when the browser says it is idle. A url already
 * queued is promoted by being pushed again at the better tier: the old
 * entry is skipped when it comes up, because `state` says it is no
 * longer queued.
 *
 * DECODED, NOT JUST FETCHED. A photograph that has arrived can still
 * paint in bands while the decoder works through it, which is the
 * complaint this exists to answer. `fetch` here is expected to resolve
 * only once the image is decoded and ready to be drawn.
 *
 * The browser's own cache is the store. Nothing is kept in memory here
 * — a Map of 300 short strings is the whole footprint.
 */

export type Fetch = (url: string, wanted: boolean) => Promise<void>;
export type Idle = (run: () => void) => void;

export type Ready = "queued" | "loading" | "done" | "failed";

export interface Warming {
  /** Fetch these when there is nothing better to do. */
  warm(urls: Iterable<string>, tier?: number): void;
  /** Fetch these now: the reader is looking at them. */
  urgent(urls: Iterable<string>): void;
  /** What is known about a url. */
  readonly state: Map<string, Ready>;
  /** How many are in flight. */
  inFlight(): number;
  /** How many are still waiting, at any tier. */
  waiting(): number;
}

export function warming(
  fetch: Fetch,
  idle: Idle,
  width = 4,
  tiers = 3,
): Warming {
  const state = new Map<string, Ready>();
  const urgentlyWanted = new Set<string>();
  const lanes: string[][] = Array.from({ length: tiers }, () => []);
  let running = 0;
  let pumping = false;

  const next = (): string | undefined => {
    for (const lane of lanes) {
      while (lane.length) {
        const url = lane.shift() as string;
        // Promoted, already fetched, or in flight: the entry is stale.
        if (state.get(url) === "queued") return url;
      }
    }
    return undefined;
  };

  const pump = (): void => {
    while (running < width) {
      const url = next();
      if (!url) return;
      state.set(url, "loading");
      running += 1;
      /* `wanted` is true for what the reader is looking at or about to
       * reach. The page turns it into a fetch priority: warming must
       * never be in front of something being waited for. */
      fetch(url, urgentlyWanted.has(url)).then(
        () => { state.set(url, "done"); },
        () => { state.set(url, "failed"); },
      ).then(() => {
        running -= 1;
        /* One failure must not stop the queue, and one success must not
         * run the rest of it inside this callback — `pump` is called
         * again, not recursed into. */
        pump();
      });
    }
  };

  const soon = (): void => {
    if (pumping) return;
    pumping = true;
    idle(() => { pumping = false; pump(); });
  };

  const put = (urls: Iterable<string>, tier: number): string[] => {
    const added: string[] = [];
    for (const url of urls) {
      if (!url) continue;
      const known = state.get(url);
      if (known === "done" || known === "loading") continue;
      // `failed` is retried: a url that failed while the page was
      // loading may well work when the reader actually needs it.
      state.set(url, "queued");
      added.push(url);
    }

    const lane = lanes[Math.min(Math.max(tier, 0), tiers - 1)];
    /* TIER 0 GOES TO THE FRONT OF TIER 0.
     *
     * Appending was right while nothing else used this tier, and the
     * check that protected it queued the other work one tier DOWN — so
     * "the reader's own request jumps the queue, however long the queue
     * is" was true of the fixture and not of the page. Measured on the
     * real page: 148 of the 150 photographs are within three screens of
     * the middle of it, and all of them were being promoted here, so a
     * project the reader opened joined the back of a queue of 148.
     *
     * The most recent thing asked for is the thing being waited for, so
     * it goes first — and a project's own photographs keep their order
     * among themselves, which is why this is one `unshift` of the whole
     * set and not one per url.
     */
    if (tier <= 0) lane?.unshift(...added);
    else lane?.push(...added);
    return added;
  };

  return {
    state,
    warm(urls, tier = tiers - 1) {
      if (put(urls, tier).length) soon();
    },
    urgent(urls) {
      const added = put(urls, 0);
      for (const url of added) urgentlyWanted.add(url);
      if (added.length) pump();
    },
    inFlight: () => running,
    waiting: () => lanes.reduce(
      (n, lane) => n + lane.filter((u) => state.get(u) === "queued").length, 0),
  };
}


/** What a browser will say about the connection, where it says anything. */
export interface Line {
  readonly saveData?: boolean;
  readonly effectiveType?: string;
}

/** Is it fair to fetch the big copies before anyone has asked for them?
 *
 *  The small photographs are 7.6MB and the bigger copies another 8.3MB.
 *  Warming the first set is the difference between a page that
 *  assembles itself and one that is simply there, and it is worth the
 *  bytes. Warming the SECOND set is a convenience — it saves a wait
 *  when a reference is opened — and sixteen megabytes of it on a phone
 *  with a data allowance is not a convenience at all.
 *
 *  So the big copies are warmed only where the browser says there is
 *  room for them. Where it says nothing — Safari has no Network
 *  Information API — the answer is yes: that is the desktop case and
 *  the one where it costs least.
 */
export function worthWarmingBigCopies(
  line: Line | undefined,
  phoneLike = false,
): boolean {
  if (line?.saveData) return false;

  /* A MEASUREMENT BEATS A GUESS. A browser that reports the line is
   * believed, whatever shape the device is: a phone on 4g was always
   * allowed these, and that has not changed. */
  const kind = line?.effectiveType;
  if (kind) return kind === "4g" || kind === "5g";

  /* AND WHERE NOTHING IS SAID, THE SHAPE OF THE DEVICE IS THE SIGNAL.
   *
   * This returned `true` — reasoned as "no API means desktop, where it
   * costs least". Safari is the browser with no Network Information
   * API, and Safari is also every iPhone, so the one case this function
   * exists to prevent — 8.3MB of photographs nobody asked for, on a
   * phone with an allowance — was the case it allowed. The client
   * approves this page on a phone.
   *
   * A coarse pointer on a small screen is a phone as far as a browser
   * will admit. Nothing is lost by waiting: the big copy is still
   * fetched the moment a reference or a project is opened, which is
   * `work.ts`, and that path is urgent. What stops is the speculative
   * 8.3MB for photographs that may never be looked at.
   */
  return !phoneLike;
}
