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
import { shiftFor } from "./drift.js";
import { animateScroll, type ScrollEnv } from "./scroll.js";

/* Both failsafes in one place, so the ordering between them is visible.
 * The cover's lives in the inline script in the head and is 6000ms;
 * this one must come after it. */
const MOTION_FAILSAFE_MS = 7000;

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---- blocks arrive on scroll -----------------------------------------
 * In two halves, and the split matters.
 *
 * `.reveal` is `opacity: 0`. Added after the cover had already lifted, it
 * blanked a page the visitor was looking at: the page faded in whole,
 * every block went transparent, and they then faded back one at a time.
 * A page appearing and then vanishing is a far worse first impression
 * than no animation at all.
 *
 * So the marking happens while the cover is still up, and only the
 * observing waits for it to lift.
 */
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

/* One observer for the whole page. `once` is deliberate: a block that has
 * arrived stays arrived, because re-animating on the way back up reads as
 * a glitch rather than as an effect.
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

  const seen = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("in");
        seen.unobserve(entry.target);
      }
    },
    // Fire a little before the block's top edge arrives, so the motion
    // finishes about where the eye lands rather than after it.
    { rootMargin: "0px 0px -12% 0px", threshold: 0.01 },
  );

  for (const el of blocks) seen.observe(el);
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
      // Below the fold, wait for the reader to arrive.
      const seen = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (!e.isIntersecting) continue;
            e.target.classList.add("in");
            seen.unobserve(e.target);
          }
        },
        { threshold: 0.1 },
      );
      seen.observe(h);
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
const WIDE = matchMedia("(min-width: 50rem)");

function syncBar(): void {
  const menu = document.querySelector<HTMLDetailsElement>(".menu");
  if (!menu) return;
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
let marker: { lock: (id: string) => void; release: (id: string) => void } | null = null;

function markCurrentSection(): void {
  const links = new Map<string, HTMLAnchorElement>();
  for (const a of document.querySelectorAll<HTMLAnchorElement>(".links a")) {
    const id = a.getAttribute("href")?.replace("#", "");
    if (id) links.set(id, a);
  }
  if (links.size === 0) return;

  const sections: Array<[string, HTMLElement]> = [];
  for (const id of links.keys()) {
    const el = document.getElementById(id);
    if (el) sections.push([id, el]);
  }
  if (sections.length === 0) return;

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
  function pick(): void {
    if (locked) {
      apply(locked);
      return;
    }
    const line = window.innerHeight * 0.25;
    const atBottom =
      window.scrollY + window.innerHeight >=
      document.documentElement.scrollHeight - 2;

    // Read every top first, write one class after — no layout thrash.
    const tops = sections.map(([id, el]) => [id, el.getBoundingClientRect().top] as const);

    let current = "";
    if (atBottom) {
      current = tops[tops.length - 1]?.[0] ?? "";
    } else {
      for (const [id, top] of tops) {
        if (top <= line) current = id;
      }
    }

    apply(current);
  }

  function apply(current: string): void {
    if (current === marked) return;
    marked = current;

    for (const [id, a] of links) {
      const on = id === current;
      a.classList.toggle("current", on);
      // The same fact, for a reader who cannot see the rule under it.
      if (on) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
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
  function request(): void {
    const now = Date.now();
    clearTimeout(trailing);
    if (now - last >= 80) {
      last = now;
      pick();
    } else {
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
    lock(id: string): void {
      if (!links.has(id)) return;
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
    release(id: string): void {
      if (!locked || locked !== id) return;
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
function closeMenuOnNavigate(): void {
  const menu = document.querySelector<HTMLDetailsElement>(".menu");
  if (!menu) return;
  menu.addEventListener("click", (ev) => {
    // Only below the breakpoint. Closing it on a wide screen would take
    // the whole bar away on the first click.
    if (WIDE.matches) return;
    if ((ev.target as HTMLElement).closest(".links a")) menu.open = false;
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
function showTheRelease(): void {
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

function photographsDrift(): void {
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
const PRESS_MS = 140;

/* ---- one scroll, ours --------------------------------------------------
 * Both the band and the buttons used `scrollIntoView({behavior:
 * "smooth"})`. That hands the speed to the browser, which chooses it
 * differently depending on the distance and differently again between
 * Safari and Chrome — so the two never matched, and neither could be
 * slowed.
 *
 * This is the same movement for every in-page link, at a speed we set.
 *
 * It yields to the reader: a wheel, a touch or a key during the
 * animation stops it where it is. A page that keeps travelling after
 * someone has started scrolling themselves is fighting them.
 */
let stopScrolling: (() => void) | null = null;

/* The browser's half of the scroll: a clock, a frame scheduler, a
 * scrollbar, and the three events that mean "I'll take it from here".
 * The loop itself is in scroll.ts, where it can be tested. */
const INTERRUPTIONS = ["wheel", "touchstart", "keydown"] as const;

const browserScroll: ScrollEnv = {
  now: () => performance.now(),
  position: () => window.scrollY,
  moveTo: (y) => window.scrollTo(0, y),
  frame: (cb) => requestAnimationFrame(cb),
  cancelFrame: (h) => cancelAnimationFrame(h),
  whenInterrupted(give) {
    for (const ev of INTERRUPTIONS) {
      addEventListener(ev, give, { passive: true, once: true });
    }
    return () => {
      for (const ev of INTERRUPTIONS) removeEventListener(ev, give);
    };
  },
};

function scrollTo(top: number, onSettled?: () => void): void {
  // A newer journey replaces an older one, and the older one settles
  // rather than being dropped — whoever was waiting on it still gets
  // its ending.
  stopScrolling?.();

  if (reduced) {
    window.scrollTo(0, top);
    onSettled?.();
    return;
  }

  const abandon = animateScroll(browserScroll, top, () => {
    stopScrolling = null;
    onSettled?.();
  });
  stopScrolling = abandon;
}

function keepOneAddress(): void {
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

  for (const a of document.querySelectorAll<HTMLAnchorElement>('a[href^="#"]')) {
    a.addEventListener("click", (ev) => {
      const id = a.getAttribute("href")?.slice(1);
      const target = id ? document.getElementById(id) : null;
      if (!target) return;              // let the browser deal with it

      ev.preventDefault();

      // The band knows where we are going before we get there.
      marker?.lock(id as string);

      // Only the buttons wait. They have a press to finish — the nav
      // band has nothing to show, and a pause there is just a delay.
      const wait = !reduced && a.classList.contains("btn") ? PRESS_MS : 0;

      setTimeout(() => {
        // Where the section's top should come to rest: under the bar,
        // which is what `scroll-margin-top` was doing for the native
        // version and has to be done by hand now.
        const bar = document.querySelector("header");
        const offset = bar ? bar.getBoundingClientRect().height : 0;
        scrollTo(
          window.scrollY + target.getBoundingClientRect().top - offset,
          // The band stops guessing where the reader is the moment the
          // journey actually ends — arrived, or abandoned.
          () => marker?.release(id as string),
        );
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
 * Once, and never again — `unobserve` on the first crossing, and the
 * transition is removed with the class that carried it.
 */
const SWAP_DONE_MS = 1400;    // the 820ms journey plus its 480ms delay, rounded up

function exchangePhrases(): void {
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

  /* A few pixels sideways as well, in opposite directions, so the two
   * pass each other rather than sliding through the same column. It is
   * the difference between an exchange and a glitch. */
  first.style.transform = `translate(-0.6rem, ${apart}px)`;
  second.style.transform = `translate(0.6rem, ${-apart}px)`;

  const seen = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        seen.unobserve(entry.target);

        heading.classList.add("swapping");
        // Read the layout so the browser registers the crossed position
        // as a starting point. Without it the class and the clearing
        // are coalesced into one change and the phrases simply appear
        // in place — the animation never happens.
        void heading.offsetWidth;
        first.style.transform = "";
        second.style.transform = "";

        // Take the transition away once it has been spent, so nothing
        // that moves these phrases later — a resize, a late font —
        // animates them again. The brief asked for once.
        window.setTimeout(() => heading.classList.remove("swapping"), SWAP_DONE_MS);
      }
    },
    { threshold: 0.6 },
  );

  seen.observe(heading);
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
function closeTheCarousel(): void {
  const openOne = (): HTMLDetailsElement | null =>
    document.querySelector<HTMLDetailsElement>(".project[open]");

  addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    const box = openOne();
    if (!box) return;
    box.open = false;
    // The summary that opened it takes the focus back, or the keyboard
    // is left standing on an element that is no longer on the screen.
    box.querySelector("summary")?.focus();
  });

  for (const reel of document.querySelectorAll<HTMLElement>(".reel")) {
    reel.addEventListener("click", (ev) => {
      if (ev.target !== reel) return;
      const box = reel.closest("details");
      if (!box || !box.open) return;
      box.open = false;
      box.querySelector("summary")?.focus();
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
const SETTLE_MS = 160;

function softWhileMoving(): void {
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

/* ---- choosing a palette -----------------------------------------------
 * An instrument for deciding, not a feature: the control is only
 * rendered while `live = false`, and the finished site has one palette.
 *
 * Switching RELOADS the page rather than swapping the tokens in place.
 * That is deliberate and it is the cheaper answer:
 *
 *   - the loader appears by itself, which is the "waiting animation in
 *     between" that was asked for. No second mechanism, no second thing
 *     that can get the sequence wrong.
 *   - the choice is read before first paint by the inline script in the
 *     head, so the page arrives already in its palette instead of
 *     changing colour after it has been seen.
 *
 * Swapping tokens live would avoid the reload and reintroduce exactly
 * the class of bug that cost most of a day: two things changing the
 * page's appearance at once.
 */
const PALETTES: readonly string[] = ["cool", "cream"];

function paletteControl(): void {
  const button = document.querySelector<HTMLButtonElement>("[data-palette-toggle]");
  if (!button) return;

  // `noUncheckedIndexedAccess` is on, so an index is `string | undefined`
  // whatever the array literally holds. The fallbacks are not defensive
  // noise — they are what makes this compile honestly.
  const current = document.documentElement.dataset["palette"] ?? PALETTES[0] ?? "cool";
  const after = PALETTES[(PALETTES.indexOf(current) + 1) % PALETTES.length];
  const next = after ?? "cool";

  button.textContent = `Palette: ${current} → ${next}`;

  button.addEventListener("click", () => {
    try {
      localStorage.setItem("palette", next);
    } catch {
      // Private browsing refuses storage. Switch for this view anyway
      // rather than appearing to do nothing.
      document.documentElement.dataset["palette"] = next;
      return;
    }
    location.reload();
  });
}

/* ---- copy the address -------------------------------------------------
 * Only ever rendered when a verified address is configured, so there is
 * nothing here to copy while the contact section is in its pending state.
 */
function copyButtons(): void {
  for (const btn of document.querySelectorAll<HTMLButtonElement>("[data-copy]")) {
    // Captured ONCE, outside the handler. Read inside it, a second click
    // within the 2.5s window captured "Copied" as the original label and
    // restored that for ever — the button then lied about what it said.
    const said = btn.textContent;
    let restore = 0;

    btn.addEventListener("click", async () => {
      const value = btn.dataset["copy"];
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        btn.textContent = "Copied";
      } catch {
        // Clipboard access can be refused, and silently failing would
        // leave someone believing they had the address.
        btn.textContent = "Copy failed — select it by hand";
      }
      clearTimeout(restore);
      restore = window.setTimeout(() => { btn.textContent = said; }, 2500);
    });
  }
}

/* ---- showing the page -------------------------------------------------
 * myBureau's sequence, which is the one that works:
 *
 *   `.is-leaving` keeps the overlay painted while `booting` comes off,
 *   it fades, and then it is REMOVED from the document.
 *
 * Removing it matters. Left in place with `visibility: hidden` it is a
 * covered page one stale class away from being covered again, and it
 * holds a state nothing else can see.
 *
 * The page underneath is finished the whole time — the fade of the cover
 * IS the transition, and nothing else moves with it.
 */
function reveal(): void {
  const loader = document.querySelector<HTMLElement>(".loader");
  if (!loader) {
    document.documentElement.classList.remove("booting");
    return;
  }

  loader.classList.add("is-leaving");
  document.documentElement.classList.remove("booting");

  if (reduced) {
    loader.remove();
    return;
  }

  void loader
    .animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: 420,
      easing: "cubic-bezier(.4,0,.6,1)",
      fill: "forwards",
    })
    .finished.then(() => loader.remove());
}

/* Start at the top, every time.
 *
 * Browsers restore the previous scroll position on reload, which happens
 * underneath the cover — so the cover would lift onto wherever the
 * reader had got to last time, mid-section, with the hero never seen. On
 * a one-page site that is held back until it is whole, the top is the
 * only sensible place to arrive. */
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

/* Prepared under the cover, started when it lifts. Doing both at once is
 * what blanked the page after it had already appeared. */
function prepareMotion(): void {
  splitHeadlines();
  markReveals();
}

function startMotion(): void {
  releaseHeadlines();
  observeReveals();
}

if (!reduced) prepareMotion();

syncBar();
WIDE.addEventListener("change", syncBar);
markCurrentSection();
closeMenuOnNavigate();
copyButtons();
paletteControl();
softWhileMoving();
exchangePhrases();
closeTheCarousel();
keepOneAddress();
photographsDrift();
showTheRelease();

/* LAST, and the ONLY place the page is shown.
 *
 * There must be exactly one of these. There were briefly two — an older
 * `uncover()` alongside this — and they ran in order: the first removed
 * `booting`, which takes the cover away instantly because `.loader` is
 * `display: none` without it; the second then added `.is-leaving`, which
 * put the cover BACK so it could fade. Page, loader, page. If a second
 * way to reveal the page is ever added, this one must go.
 *
 * `load`, not `DOMContentLoaded`: the point of covering the page is to
 * wait for the photographs. With no lazy attribute on them they are all
 * in flight from the start, so this is the moment it is genuinely whole.
 * The 6s failsafe in the head covers anything that goes wrong here. */
function show(): void {
  reveal();
  if (!reduced) startMotion();
}

if (document.readyState === "complete") show();
else window.addEventListener("load", show, { once: true });
