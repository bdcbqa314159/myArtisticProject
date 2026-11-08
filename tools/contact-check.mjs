/* What the form refuses.
 *
 *     node tools/contact-check.mjs
 *
 * The checks in src/contact.ts are pure so that they can be run here,
 * which is the only reason any of them are checked at all — the browser
 * half cannot be driven in this harness.
 *
 * Worth repeating what the module itself says: none of this is a
 * defence. An attacker POSTs straight at the endpoint and not one line
 * of it executes. These are the honest-mistake catchers and the
 * lazy-bot tax. What they must NOT do is refuse a real message.
 */
import assert from "node:assert/strict";
import { checkAll, checkEmail, checkMessage, checkSubject, clean, LIMITS }
  from "../static/js/contact.js";

const ok = (c, what) => assert.equal(c.ok, true, `${what}: ${c.why ?? ""}`);
const no = (c, why, what) => {
  assert.equal(c.ok, false, `${what} was accepted`);
  assert.equal(c.why, why, `${what} gave ${c.why}`);
};

const NUL = "\u0000";

/* ---- addresses people really have -------------------------------------
 * A refusal that is too broad is the worse bug: a visitor with a real
 * address who cannot send is an enquiry nobody ever hears about, and
 * nobody reports it either. */
for (const good of [
  "a@b.co", "prenom@example.fr", "first.last@studio.example.com",
  "a+tag@example.co.uk", "o'brien@example.ie",
  "very.long.but.fine@sub.domain.example.org",
]) ok(checkEmail(good), `a real address ${good}`);

no(checkEmail(""), "err_mail_missing", "no address");
no(checkEmail("   "), "err_mail_missing", "an address of spaces");
no(checkEmail("a".repeat(250) + "@b.co"), "err_mail_long", "an over-long address");
no(checkEmail("a@b.co, c@d.co"), "err_mail_one", "two addresses");
no(checkEmail("a@b.co; c@d.co"), "err_mail_one", "two addresses, semicolon");
no(checkEmail("nobody"), "err_mail_invalid", "no @ at all");
no(checkEmail("a@b"), "err_mail_invalid", "no dot in the domain");
no(checkEmail("a @b.co"), "err_mail_invalid", "a space inside");

/* THE ONE THAT MATTERS. A newline in a field that becomes a mail header
 * lets an attacker append their own, and the mail goes out in his name. */
no(checkEmail("a@b.co\nBcc: everyone@example.com"), "err_mail_invalid",
   "a header smuggled into the address");
no(checkEmail("a@b.co\r\nTo: someone@example.com"), "err_mail_invalid",
   "a CRLF header");
no(checkEmail("a@b.co" + NUL), "err_mail_invalid", "a NUL in the address");

ok(checkSubject(""), "no subject at all, which is allowed");
ok(checkSubject("A project in Marseille"), "an ordinary subject");
no(checkSubject("x".repeat(LIMITS.subject + 1)), "err_subject", "an over-long subject");
no(checkSubject("hi\nBcc: everyone@example.com"), "err_subject",
   "a header smuggled into the subject");
no(checkSubject("hi" + NUL + "there"), "err_subject", "a control character");

ok(checkMessage("Bonjour, j'aimerais parler d'un projet."), "an ordinary message");
ok(checkMessage("Here is one link: https://example.com"), "a message with a link");
ok(checkMessage("line one\nline two"), "newlines, which are fine in a body");
no(checkMessage(""), "err_message_missing", "an empty message");
no(checkMessage("x".repeat(LIMITS.message + 1)), "err_message_long", "an over-long message");
no(checkMessage("a" + NUL + "b"), "err_message_bad", "a NUL in the message");
no(checkMessage("\nBcc: a@b.co"), "err_message_bad", "a header in the message");
no(checkMessage(Array(8).fill("https://x.example").join(" ")), "err_message_links",
   "eight links");
ok(checkMessage(Array(6).fill("https://x.example").join(" ")), "six links, allowed");

/* ---- the order of complaint -------------------------------------------
 * One thing at a time, and the address first: it is the field without
 * which no reply is possible, so it is the one worth fixing first. */
no(checkAll({ email: "", subject: "x".repeat(400), message: "" }),
   "err_mail_missing", "several faults at once");
no(checkAll({ email: "a@b.co", subject: "x".repeat(400), message: "" }),
   "err_subject", "the subject, once the address is sound");
ok(checkAll({ email: "a@b.co", subject: "Hello", message: "Hello." }),
   "a sound submission");

/* `clean` tidies what has already passed. It is never what makes
 * something safe — the refusals above are. */
assert.equal(clean("a" + NUL + "bc"), "abc");
assert.equal(clean("keep\ttabs\nand newlines"), "keep\ttabs\nand newlines");

console.log("\n  contact: the form refuses 19 bad submissions "
  + "and accepts 13 real ones\n");
