/* The one check behind src/words.ts — a headline must survive being
 * taken apart. Run by `npm test`.
 *
 *     node tools/words-check.mjs
 */
import assert from "node:assert/strict";
import { splitWords, rejoin } from "../static/js/words.js";

const cases = [
  "Two worlds, one crossover.",
  "A multidisciplinary Creative Agency built for the cultural economy.",
  "Créer des expériences — à la croisée du mouvement",   // accents, em dash
  "one",
  "  leading and trailing  ",
  "double  space inside",
  "line\nbreak",
];

for (const text of cases) {
  const parts = splitWords(text);
  // Nothing is lost: what a screen reader hears is what was written.
  assert.equal(rejoin(parts), text, `round trip failed for ${JSON.stringify(text)}`);
  // Words carry no whitespace, so none of them can be an empty box.
  for (const p of parts) {
    if ("word" in p) assert.ok(p.word.length > 0 && !/\s/.test(p.word), `bad word in ${JSON.stringify(text)}`);
  }
}

// The stagger is capped at 14 in CSS; this is the fact that cap assumes.
assert.equal(splitWords("Two worlds, one crossover.").filter((p) => "word" in p).length, 4);
assert.deepEqual(splitWords(""), []);
assert.deepEqual(splitWords("   "), [{ space: "   " }]);

console.log("  words: %d headlines survive the round trip", cases.length);
