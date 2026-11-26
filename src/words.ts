/* Splitting a headline into words, as a pure function, so the awkward
 * parts can be tested without a browser.
 *
 * FIRST AWKWARD PART: the spaces. Wrap each word in an element and drop
 * the whitespace, and "Two worlds, one crossover." is read aloud by a
 * screen reader as "Twoworlds,onecrossover." — so the separators are
 * returned alongside the words and put back as real text.
 *
 * SECOND AWKWARD PART: a sentence set in two faces. The direction the
 * client's designer is going is one line carrying two typefaces, so a
 * headline is no longer a flat string — it is a sequence of RUNS, each
 * in one face or the other.
 *
 * A word can straddle a run. "experi" in one face and "ences" in the
 * other is a legitimate thing for a designer to ask for, and it must
 * not become two words: the box around a word is what clips its
 * entrance, and two boxes would let a line break fall inside a word.
 * So a word is not a string here, it is its own little sequence of
 * runs, and the box goes around all of them.
 */

/** A stretch of text in one face or the other. */
export interface Run {
  readonly text: string;
  /** True for the second face — `.other-face` in the page.
   *
   *  Explicitly `| undefined`: the splitter copies this field across
   *  from the run a word came from, and `exactOptionalPropertyTypes`
   *  refuses a copied `undefined` into an optional that does not admit
   *  it. Saying so here is honest about what the field holds. */
  readonly other?: boolean | undefined;
}

export type Part = { word: Run[] } | { space: string };

/** The words and the spaces between them, each word keeping its faces. */
export function splitWords(runs: readonly Run[]): Part[] {
  const parts: Part[] = [];

  for (const run of runs) {
    // \s+ keeps the original run of whitespace rather than normalising
    // it, so a deliberate double space or a newline survives the round
    // trip.
    for (const chunk of run.text.split(/(\s+)/)) {
      if (chunk === "") continue;

      if (/^\s+$/.test(chunk)) {
        parts.push({ space: chunk });
        continue;
      }

      /* THE JOIN. A run boundary inside a word is not a word boundary:
       * if the last part is a word and no space has come between, this
       * chunk belongs to it. That is the whole reason a word holds
       * runs rather than a string. */
      const last = parts[parts.length - 1];
      if (last && "word" in last) {
        last.word.push({ text: chunk, other: run.other });
      } else {
        parts.push({ word: [{ text: chunk, other: run.other }] });
      }
    }
  }

  return parts;
}

/** The text a screen reader would hear, from the parts. */
export function rejoin(parts: readonly Part[]): string {
  return parts
    .map((p) => ("word" in p
      ? p.word.map((r) => r.text).join("")
      : p.space))
    .join("");
}

/** Plain text, for the common case of a headline in one face. */
export function fromText(text: string): Run[] {
  return [{ text }];
}
