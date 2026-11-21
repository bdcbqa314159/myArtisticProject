/* How the page moves.
 *
 * The reveals and the headlines released word by word, the two phrases
 * exchanging places, the photographs drifting as the page scrolls, the
 * smear a fast scroll leaves, the press a button answers with, and the
 * stillness all of it keeps while someone is scrolling.
 *
 * Every one of them is off under `prefers-reduced-motion`, which is
 * read once in `reduced.ts` and consulted here.
 */

import { splitWords } from "./words.js";
import { shiftFor } from "./drift.js";
import { whileInView } from "./arrive.js";
import { swapOnArrival } from "./swap.js";
import { reduced } from "./reduced.js";
import type { Seen } from "./arrive.js";

const MOTION_FAILSAFE_MS = 7000;

function markReveals(): void {
  // Everything except the hero. The hero is what the wait was for: when
  // the cover dissolves it should already be there, whole, rather than
  // starting a second animation the moment the first one ends. Blocks
  // further down have not been waited for and can arrive as you reach
  // them.
  for (const el of document.querySelectorAll<HTMLElement>("section:not(.hero) > .wrap > *")) {
    el.classList.add("reveal");
  }
}

/* What `whileInView` needs from this page: a real observer, and what
 * "marked" means here — the class both reveals are driven by. */
export const watcher = (
  cb: (entries: Seen[]) => void,
  options: { rootMargin?: string; threshold?: number },
): IntersectionObserver =>
  new IntersectionObserver(cb as IntersectionObserverCallback, options);

export const released = (el: Element, on: boolean): void => {
  el.classList.toggle("in", on);
};

/* Two observers for the whole page: one for arriving, one for leaving.
 *
 * It used to be one, and it unobserved: a block that had arrived stayed
 * arrived, on the grounds that re-animating on the way back up reads as
 * a glitch. Watched on the page, it reads as the opposite — "the title
 * stays in place and no animation", a section that was alive the first
 * time and dead every time after. The client asked for it to play on
 * every arrival.
 *
 * WHY TWO, AND WITH DIFFERENT MARGINS. Arriving fires early, 12% before
 * the block's top edge lands, so the motion finishes about where the
 * eye does. Leaving must NOT use that margin: with 12% shaved off the
 * bottom of the root, a block scrolled back towards from below would
 * stop "intersecting" while still visibly on screen, and the words
 * would retract in front of the reader. So the leave observer uses the
 * viewport exactly: a block is reset only once it is entirely out of
 * sight, where the reset costs nothing and is seen by nobody.
 */
function observeReveals(): void {
  const blocks = document.querySelectorAll<HTMLElement>(".reveal");

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
    if (box.top < window.innerHeight && box.bottom > 0) el.classList.add("in");
  }

  // The wiring is in arrive.ts, where it can be checked: a browser
  // here runs the page in an iframe, and an IntersectionObserver
  // callback needs a rendering opportunity, which an iframe never gets.
  whileInView(blocks, watcher, released);
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
function splitHeadlines(): void {
  // DOM surgery only. Nothing is released here — see releaseHeadlines().
  for (const h of document.querySelectorAll<HTMLElement>("h1, section h2")) {
    if (h.childElementCount > 0) continue;
    const text = h.textContent;
    if (!text || !text.trim()) continue;

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
function releaseHeadlines(): void {
  for (const h of document.querySelectorAll<HTMLElement>(".split")) {
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
    } else {
      // Below the fold, wait for the reader to arrive — and arrive
      // again. A tenth of the headline in view is enough, and no
      // margin: a headline is short, and the words should not start
      // before it is on screen.
      whileInView([h], watcher, released, "0px", 0.1);
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
    for (const h of document.querySelectorAll(".split")) h.classList.add("in");
    for (const el of document.querySelectorAll(".reveal")) el.classList.add("in");
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
const SMEAR_MAX = 7;          // the most it ever blurs, in px — looked at, not guessed
const SMEAR_PER_PX = 0.08;    // blur per pixel of movement in one frame

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
  const first = document.querySelector<HTMLElement>(".case .image img");
  if (!first) return null;
  first.classList.add("smear");

  return (velocity: number): void => {
    const amount = Math.min(SMEAR_MAX, Math.abs(velocity) * SMEAR_PER_PX);
    blur.setAttribute("stdDeviation", `0 ${amount.toFixed(2)}`);
    // Behind the movement: scrolling down drags the trail upward.
    offset.setAttribute("dy", (-Math.sign(velocity) * amount * 0.7).toFixed(2));
  };
}

export function photographsDrift(): void {
  if (reduced) return;

  const shots = document.querySelectorAll<HTMLElement>(".case .image img");
  if (shots.length === 0) return;

  const onScreen = new Set<HTMLElement>();
  const smearTo = smear();
  let frame = 0;
  let lastY = window.scrollY;

  function draw(): void {
    frame = 0;
    const height = window.innerHeight;

    // How far the page moved since the last frame. One subtraction, and
    // it is the only thing the smear needs.
    const velocity = window.scrollY - lastY;
    lastY = window.scrollY;
    if (smearTo) smearTo(velocity);
    for (const img of onScreen) {
      const box = img.getBoundingClientRect();
      const shift = shiftFor(box.top, box.height, height, PARALLAX_PX);
      img.style.transform = `translate3d(0, ${shift.toFixed(1)}px, 0)`;
    }
  }

  function request(): void {
    if (!frame && onScreen.size > 0) frame = requestAnimationFrame(draw);
  }

  const seen = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        const img = e.target as HTMLElement;
        if (e.isIntersecting) {
          onScreen.add(img);
        } else {
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
    { rootMargin: "120px 0px" },
  );

  for (const img of shots) seen.observe(img);

  addEventListener("scroll", request, { passive: true });
  addEventListener("resize", request, { passive: true });

  // The page stops between frames, not on an event, so the last frame
  // can leave a smear frozen on a still photograph. This settles it.
  let settle = 0;
  addEventListener(
    "scroll",
    () => {
      clearTimeout(settle);
      settle = window.setTimeout(() => smearTo?.(0), 120);
    },
    { passive: true },
  );
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
const SWAP_DONE_MS = 1400;    // the 820ms journey plus its 480ms delay, rounded up

export function exchangePhrases(): void {
  // No crossing at all under reduced motion: the heading is simply the
  // heading, already in the right order.
  if (reduced) return;

  const heading = document.querySelector<HTMLElement>(".swap");
  if (!heading) return;

  const phrases = heading.querySelectorAll<HTMLElement>(".phrase");
  const first = phrases[0];
  const second = phrases[1];
  if (!first || !second || phrases.length !== 2) return;

  const apart = second.offsetTop - first.offsetTop;
  // Stacked by a stylesheet that has not loaded, or laid out side by
  // side by some future change: either way there is no vertical journey
  // to make, and a swap of nothing is worse than none.
  if (apart <= 0) return;


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
  /* Where they wait until the section is reached, and where they are
   * put back once it has gone. The animation's own first frame is this
   * same position, so nothing jumps when it starts.
   *
   * MEASURED EVERY TIME, not once. The distance between the phrases is
   * what the arc is drawn from, and it changes with the width of the
   * page and with a font arriving late — so a swap parked at the old
   * distance would travel the wrong way. Transforms do not affect
   * layout, so reading `offsetTop` while they are parked is safe. */
  const park = (): void => {
    const gap = second.offsetTop - first.offsetTop;
    if (gap <= 0) return;

    const ink = document.createRange();
    ink.selectNodeContents(first);
    const inked = ink.getBoundingClientRect();
    const edge = inked.width > 0 ? inked.left : first.getBoundingClientRect().left;
    const reach = Math.max(0, Math.min(gap * 0.72, edge - 4));

    first.style.setProperty("--from-y", `${gap}px`);
    first.style.setProperty("--bow", `${reach}px`);
    second.style.setProperty("--from-y", `${-gap}px`);
    second.style.setProperty("--bow", `${reach * 0.42}px`);
    first.style.transform = `translateY(${gap}px)`;
    second.style.transform = `translateY(${-gap}px)`;
  };

  /* The sequence is in swap.ts, where the one thing that can silently
   * break — leaving mid-flight — can be checked. `whileInView` is the
   * same pair of observers the reveals use: arriving on 60% of the
   * heading, resetting only once it is entirely out of sight. */
  const staged = swapOnArrival({
    park,
    play: () => heading.classList.add("swapping"),
    stop: () => heading.classList.remove("swapping"),
    rest: () => {
      first.style.transform = "";
      second.style.transform = "";
    },
    after: (ms, run) => window.setTimeout(run, ms),
    cancel: (timer) => window.clearTimeout(timer),
  }, SWAP_DONE_MS);

  park();
  whileInView([heading], watcher, (_el, on) => staged(on), "0px", 0.6);
}

/* ---- warming the photographs, quietly --------------------------------
 * Measured on the built page: seventeen images block the cover — 0.4MB,
 * the first screen — and a hundred and fifty more are `loading="lazy"`,
 * 7.6MB of them, arriving as the reader reaches them. A section
 * assembling itself in front of whoever scrolled to it is the thing
 * this is for: "I really do not want to see the pictures appearing by
 * shreds".
 *
 * The cover is not the answer. Holding the page until all of it had
 * arrived would mean sixteen megabytes before the first word. So the
 * page still opens on its first screen, and the rest is fetched behind
 * it, in reading order, at four at a time, only while the browser says
 * it is idle — `preload.ts` holds that queue, and what the reader
 * opens jumps it.
 *
 * DECODED BEFORE IT COUNTS AS READY. `img.decode()` resolves when the
 * photograph can be drawn, not merely when its bytes have arrived —
 * which is the difference between a picture appearing and a picture
 * appearing in bands.
 */
const SETTLE_MS = 160;

export function softWhileMoving(): void {
  // Under reduced motion there is no blur at all: for some readers this
  // is not an effect, it is motion sickness.
  if (reduced) return;

  const root = document.documentElement;
  let settle = 0;

  addEventListener(
    "scroll",
    () => {
      if (!root.classList.contains("scrolling")) root.classList.add("scrolling");
      clearTimeout(settle);
      settle = window.setTimeout(() => root.classList.remove("scrolling"), SETTLE_MS);
    },
    { passive: true },
  );
}

export function prepareMotion(): void {
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
const SETTLED_MS = 160;   // long enough to bridge the gaps between events

function stillWhileScrolling(): void {
  const cloud = document.querySelector<HTMLElement>(".cloud");
  if (!cloud) return;

  let settling = 0;
  addEventListener(
    "scroll",
    () => {
      cloud.classList.add("held");
      window.clearTimeout(settling);
      settling = window.setTimeout(() => cloud.classList.remove("held"),
                                   SETTLED_MS);
    },
    { passive: true },
  );
}

export function startMotion(): void {
  releaseHeadlines();
  observeReveals();
  stillWhileScrolling();
}

/* ---- starting up, one piece at a time ---------------------------------
 *
 * These used to be thirteen bare calls in a row, and a module is one
 * statement after another: the first that throws ends the whole of it.
 * Measured, with a fault injected at the third of them — the page sat
 * behind its cover for the full six seconds of the failsafe in the
 * head, and then arrived with NO navigation at all. The menu did
 * nothing, the palette never changed, the gallery never bound. Only
 * the contact form survived, because it is a separate module.
 *
 * None of these needs the others. A page with no drifting photographs
 * is a page with no drifting photographs; it is not a page whose menu
 * is dead. So each stands on its own, and a failure is written where a
 * developer will find it rather than taken out on the reader.
 */
/* ---- where each light sits ------------------------------------------
 * The prints overlap, so a light fixed at the foot of every one of them
 * disappears under its neighbour in a few arrangements. A project can
 * therefore name its own spot — `look = "33 77"` — and this puts it
 * there.
 *
 * WRITTEN HERE, NOT IN THE MARKUP. It was a `style` attribute on the
 * element, and the policy on this page is `style-src 'self'` with no
 * `unsafe-hashes`: a style ATTRIBUTE is inline style, so the browser
 * dropped it. Measured under the page's own policy — the custom
 * property read back EMPTY — which means the escape hatch for the
 * three arrangements that need it had never once applied. A CSSOM
 * write is not inline style and is allowed, so the same two numbers
 * now arrive the way the policy permits.
 *
 * Without script the default stands, which is where the light was for
 * every reader until now anyway. */
export function showTheRelease(): void {
  if (reduced) return;

  for (const btn of document.querySelectorAll<HTMLElement>(".btn")) {
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
