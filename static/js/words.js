/* Splitting a headline into words, as a pure function, so the awkward
 * part can be tested without a browser.
 *
 * Awkward part: the spaces. Wrap each word in an element and drop the
 * whitespace, and "Two worlds, one crossover." is read aloud by a screen
 * reader as "Twoworlds,onecrossover." — so the separators are returned
 * alongside the words and put back as real text.
 */
export function splitWords(text) {
    const parts = [];
    // \s+ keeps the original run of whitespace rather than normalising it,
    // so a deliberate double space or a newline survives the round trip.
    for (const chunk of text.split(/(\s+)/)) {
        if (chunk === "")
            continue;
        if (/^\s+$/.test(chunk))
            parts.push({ space: chunk });
        else
            parts.push({ word: chunk });
    }
    return parts;
}
/** The text a screen reader would hear, from the parts. */
export function rejoin(parts) {
    return parts.map((p) => ("word" in p ? p.word : p.space)).join("");
}
//# sourceMappingURL=words.js.map