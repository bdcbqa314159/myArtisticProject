/* The one check behind src/words.ts — a headline must survive being
 * taken apart. Run by `npm test`.
 *
 *     node tools/words-check.mjs
 *
 * A headline is no longer a flat string: the client's designer is going
 * towards one line carrying two typefaces, so it arrives as a sequence
 * of runs and a WORD may straddle two of them. Everything below is
 * about not losing anything on the way through — not a letter, not a
 * space, and not the face a letter was set in.
 */
import assert from "node:assert/strict";
import { splitWords, rejoin, fromText } from "../static/js/words.js";

let checks = 0;
const is = (got, want, what) => { assert.deepEqual(got, want, what); checks++; };
const ok = (cond, what) => { assert.ok(cond, what); checks++; };

/* ---- one face, which is almost every headline ----------------------- */
const plain = [
  "Two worlds, one crossover.",
  "A multidisciplinary Creative Agency built for the cultural economy.",
  "Créer des expériences — à la croisée du mouvement",   // accents, em dash
  "one",
  "  leading and trailing  ",
  "double  space inside",
  "line\nbreak",
];

for (const text of plain) {
  const parts = splitWords(fromText(text));
  is(rejoin(parts), text,
     `nothing is lost: what a screen reader hears is what was written — ${JSON.stringify(text)}`);
  for (const p of parts) {
    if ("word" in p) {
      const word = p.word.map((r) => r.text).join("");
      ok(word.length > 0 && !/\s/.test(word),
         `a word carries no whitespace, so no box can be empty — ${JSON.stringify(text)}`);
    }
  }
}

// The stagger is capped at 14 in CSS; this is the fact that cap assumes.
is(splitWords(fromText("Two worlds, one crossover.")).filter((p) => "word" in p).length, 4,
   "four words, as the CSS stagger assumes");
is(splitWords([]), [], "nothing at all is not an error");
is(splitWords(fromText("")), [], "an empty headline is not an error");
is(splitWords(fromText("   ")), [{ space: "   " }], "whitespace alone stays whitespace");

/* ---- two faces in one sentence --------------------------------------- */
{
  const parts = splitWords([
    { text: "Ideas become " },
    { text: "experiences.", other: true },
  ]);
  is(rejoin(parts), "Ideas become experiences.",
     "a sentence in two faces still reads as one sentence");
  is(parts.filter((p) => "word" in p).length, 3, "three words");
  const last = parts[parts.length - 1];
  is(last.word, [{ text: "experiences.", other: true }],
     "and the word in the other face knows it");
}

/* ---- A WORD THAT STRADDLES THE TWO ----------------------------------- */
{
  const parts = splitWords([
    { text: "experi" },
    { text: "ences", other: true },
  ]);
  is(parts.length, 1,
     "one word, not two — the box around a word is what clips its "
     + "entrance, and two boxes would let a line break fall inside a word");
  is(parts[0].word, [
    { text: "experi", other: undefined },
    { text: "ences", other: true },
  ], "with both faces kept, in order");
  is(rejoin(parts), "experiences", "and it still reads as the word it is");
}

/* ---- a run boundary that lands exactly on a space -------------------- */
{
  const parts = splitWords([
    { text: "Ideas " },
    { text: " become", other: true },
  ]);
  is(rejoin(parts), "Ideas  become",
     "both spaces survive: a run boundary is not a licence to normalise");
  is(parts.filter((p) => "word" in p).length, 2, "and they are still two words");
}

/* ---- the other face in the middle of a line -------------------------- */
{
  const parts = splitWords([
    { text: "Built on " },
    { text: "practice", other: true },
    { text: ". Open to new territories." },
  ]);
  is(rejoin(parts), "Built on practice. Open to new territories.",
     "a run in the middle loses nothing on either side");
  const faces = parts.filter((p) => "word" in p)
    .map((p) => p.word.map((r) => (r.other ? "B" : "A")).join(""));
  is(faces, ["A", "A", "BA", "A", "A", "A", "A"],
     "and `practice.` is one word in two faces — the full stop stayed in "
     + "the first face, which is exactly the kind of detail a designer "
     + "will care about");
}

/* ---- an empty run is not a word -------------------------------------- */
{
  const parts = splitWords([{ text: "" }, { text: "word" }, { text: "" }]);
  is(parts.length, 1, "empty runs contribute nothing");
  is(rejoin(parts), "word", "and nothing is lost");
}

console.log(`\n  words: a headline survives being taken apart, in one face `
  + `or two, at ${checks} points\n`);
