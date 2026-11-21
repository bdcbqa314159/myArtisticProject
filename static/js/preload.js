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
export function warming(fetch, idle, width = 4, tiers = 3) {
    const state = new Map();
    const urgentlyWanted = new Set();
    const lanes = Array.from({ length: tiers }, () => []);
    let running = 0;
    let pumping = false;
    const next = () => {
        for (const lane of lanes) {
            while (lane.length) {
                const url = lane.shift();
                // Promoted, already fetched, or in flight: the entry is stale.
                if (state.get(url) === "queued")
                    return url;
            }
        }
        return undefined;
    };
    const pump = () => {
        while (running < width) {
            const url = next();
            if (!url)
                return;
            state.set(url, "loading");
            running += 1;
            /* `wanted` is true for what the reader is looking at or about to
             * reach. The page turns it into a fetch priority: warming must
             * never be in front of something being waited for. */
            fetch(url, urgentlyWanted.has(url)).then(() => { state.set(url, "done"); }, () => { state.set(url, "failed"); }).then(() => {
                running -= 1;
                /* One failure must not stop the queue, and one success must not
                 * run the rest of it inside this callback — `pump` is called
                 * again, not recursed into. */
                pump();
            });
        }
    };
    const soon = () => {
        if (pumping)
            return;
        pumping = true;
        idle(() => { pumping = false; pump(); });
    };
    const put = (urls, tier) => {
        const added = [];
        for (const url of urls) {
            if (!url)
                continue;
            const known = state.get(url);
            if (known === "done" || known === "loading")
                continue;
            // `failed` is retried: a url that failed while the page was
            // loading may well work when the reader actually needs it.
            state.set(url, "queued");
            lanes[Math.min(Math.max(tier, 0), tiers - 1)]?.push(url);
            added.push(url);
        }
        return added;
    };
    return {
        state,
        warm(urls, tier = tiers - 1) {
            if (put(urls, tier).length)
                soon();
        },
        urgent(urls) {
            const added = put(urls, 0);
            for (const url of added)
                urgentlyWanted.add(url);
            if (added.length)
                pump();
        },
        inFlight: () => running,
        waiting: () => lanes.reduce((n, lane) => n + lane.filter((u) => state.get(u) === "queued").length, 0),
    };
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
export function worthWarmingBigCopies(line) {
    if (!line)
        return true;
    if (line.saveData)
        return false;
    const kind = line.effectiveType;
    if (!kind)
        return true;
    return kind === "4g" || kind === "5g";
}
//# sourceMappingURL=preload.js.map