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
function markCurrentSection(): void {
  const links = new Map<string, HTMLAnchorElement>();
  for (const a of document.querySelectorAll<HTMLAnchorElement>(".links a")) {
    const id = a.getAttribute("href")?.replace("#", "");
    if (id) links.set(id, a);
  }
  if (links.size === 0) return;

  const seen = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        const a = links.get(e.target.id);
        if (!a) continue;
        a.classList.toggle("current", e.isIntersecting);
      }
    },
    { rootMargin: "-10% 0px -70% 0px" },
  );

  for (const id of links.keys()) {
    const section = document.getElementById(id);
    if (section) seen.observe(section);
  }
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

function photographsDrift(): void {
  if (reduced) return;

  const shots = document.querySelectorAll<HTMLElement>(".case .image img");
  if (shots.length === 0) return;

  const onScreen = new Set<HTMLElement>();
  let frame = 0;

  function draw(): void {
    frame = 0;
    const height = window.innerHeight;
    for (const img of onScreen) {
      const box = img.getBoundingClientRect();
      // 0 when the photograph's middle is at the top of the screen, 1 at
      // the bottom. Centred is 0.5, which is where it sits still.
      const through = (box.top + box.height / 2) / height;
      const shift = (0.5 - through) * 2 * PARALLAX_PX;
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
}

/* ---- let the press be seen ---------------------------------------------
 * "Comme la page défile très rapidement après le clic, on n'a pas
 * vraiment le temps de voir l'animation."
 *
 * The anchor jump begins on the same frame as the press, so the button
 * is already off-screen before it has finished moving. The fix is not
 * to slow the scroll — a slow scroll is its own annoyance — but to let
 * the press happen first and then leave.
 *
 * 140ms: the press transition is 110ms, so this is the button finishing
 * its movement and no more. Short enough that nobody experiences it as
 * waiting, and it is the whole delay — the scroll itself is unchanged.
 *
 * WITHOUT SCRIPT the anchors work exactly as before. This intercepts a
 * click it is fully able to complete itself, and if anything throws, the
 * browser has already been told not to navigate — so the fallback is
 * handled explicitly rather than hoped for.
 */
const PRESS_MS = 140;

function letThePressBeSeen(): void {
  if (reduced) return;

  for (const a of document.querySelectorAll<HTMLAnchorElement>('.actions a[href^="#"]')) {
    a.addEventListener("click", (ev) => {
      const id = a.getAttribute("href")?.slice(1);
      const target = id ? document.getElementById(id) : null;
      if (!target) return;                 // let the browser deal with it

      ev.preventDefault();
      setTimeout(() => {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        // The address bar should still show where you are, and Back
        // should still come back — preventDefault took both away.
        history.pushState(null, "", `#${id}`);
      }, PRESS_MS);
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
letThePressBeSeen();
photographsDrift();

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
