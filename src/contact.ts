/* The form behind "Let's talk" — what it refuses, and why.
 *
 * READ THIS BEFORE TRUSTING ANY OF IT.
 *
 * Every check here runs in the visitor's browser. An attacker does not
 * use the form: they POST straight at the endpoint with curl and none
 * of this executes. This is the sign on the door. The lock is whatever
 * validates on the receiving side.
 *
 * What it is genuinely for: catching honest mistakes, telling the sender
 * why instead of failing silently, and costing a lazy bot more than it
 * wants to spend. Worth having. Not a defence.
 *
 * Ported from myBureau, which has been running it — the engine travels
 * with the Author, LICENCE §2. The checks are the same; the words moved
 * into the content file so the French page can carry its own.
 */

export type Check = { ok: true } | { ok: false; why: string };

const OK: Check = { ok: true };
const no = (why: string): Check => ({ ok: false, why });

/** Control characters, except tab and newline, which are legal in a body. */
const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/;
const NEWLINE = /[\r\n]/;

/* The shape that turns a contact form into a spam relay: a newline in a
 * field that lands in a mail header lets an attacker append their own —
 * "Bcc: <five thousand addresses>" — and the mail goes out in his name. */
const HEADERISH =
  /(^|[\r\n])\s*(bcc|cc|to|from|reply-to|content-type|content-transfer-encoding|mime-version|x-mailer)\s*:/i;

export const LIMITS = { email: 254, subject: 150, message: 4000 } as const;

/** Strip control characters. Never a substitute for refusing — only to
 *  tidy what has already passed. */
export const clean = (s: string): string =>
  s.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");

/** Exactly one address, and nothing that could become a header. */
export function checkEmail(raw: string): Check {
  const v = raw.trim();
  if (v === "") return no("err_mail_missing");
  if (v.length > LIMITS.email) return no("err_mail_long");
  if (NEWLINE.test(v) || CONTROL.test(v)) return no("err_mail_invalid");
  if (/[,;]/.test(v)) return no("err_mail_one");
  if (HEADERISH.test(v)) return no("err_mail_invalid");
  /* Shape, deliberately not RFC 5322. A perfect address regular
   * expression is a famous trap; one @, something either side, a dot in
   * the domain is enough. The control-character ban above is the part
   * that actually matters. */
  if (!/^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/.test(v)) return no("err_mail_invalid");
  return OK;
}

/** The subject becomes a mail header, so it gets the same newline ban. */
export function checkSubject(raw: string): Check {
  const v = raw.trim();
  if (v.length > LIMITS.subject) return no("err_subject");
  if (NEWLINE.test(v) || CONTROL.test(v)) return no("err_subject");
  if (HEADERISH.test(v)) return no("err_subject");
  return OK;
}

/** The body is not a header, so injection matters less and volume more. */
export function checkMessage(raw: string): Check {
  const v = raw.trim();
  if (v === "") return no("err_message_missing");
  if (v.length > LIMITS.message) return no("err_message_long");
  if (CONTROL.test(v)) return no("err_message_bad");
  if (HEADERISH.test(v)) return no("err_message_bad");
  const links = v.match(/https?:\/\//gi);
  if (links !== null && links.length > 6) return no("err_message_links");
  return OK;
}

export interface Submission {
  email: string;
  subject: string;
  message: string;
}

export function checkAll(s: Submission): Check {
  const email = checkEmail(s.email);
  if (!email.ok) return email;
  const subject = checkSubject(s.subject);
  if (!subject.ok) return subject;
  return checkMessage(s.message);
}

/** Nobody writes an email in under two and a half seconds. Plenty of
 *  bots do. */
export const TOO_FAST_MS = 2500;

/* ---------------------------------------------------------------------
 * Wiring. Everything above is pure, so it can be imported and tested in
 * Node where there is no document — which is the only reason any of it
 * is checked at all.
 * ------------------------------------------------------------------ */

function wire(form: HTMLFormElement): void {
  const opened = Date.now();
  const slot = form.querySelector<HTMLElement>("[data-says]");
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]');
  const endpoint = form.getAttribute("action") ?? "";
  const key = form.querySelector<HTMLInputElement>('input[name="access_key"]')?.value ?? "";

  /* The words come from the page, not from here, so a second language is
   * a content change and never a code change. An unknown key shows as
   * the key — visible, and never a blank. */
  let words: Record<string, string> = {};
  try {
    words = JSON.parse(form.dataset["says"] ?? "{}") as Record<string, string>;
  } catch {
    words = {};
  }

  const tell = (why: string): void => {
    if (slot !== null) slot.textContent = words[why] ?? why;
  };

  form.addEventListener("submit", (ev: Event): void => {
    ev.preventDefault();

    /* A field no person can see and no screen reader reaches. Filled in
     * means a bot. Say nothing — an error teaches it what tripped it. */
    const trap = form.querySelector<HTMLInputElement>('input[name="_trap"]');
    if (trap !== null && trap.value !== "") return;
    if (Date.now() - opened < TOO_FAST_MS) return;

    const data = new FormData(form);
    const said: Submission = {
      email: String(data.get("email") ?? ""),
      subject: String(data.get("subject") ?? ""),
      message: String(data.get("message") ?? ""),
    };

    const verdict = checkAll(said);
    if (!verdict.ok) {
      tell(verdict.why);
      return;
    }

    // No key means no destination. Say so rather than posting into a void.
    if (endpoint === "" || key === "") {
      tell("form_offline");
      return;
    }

    if (button !== null) button.disabled = true;      // one click, one mail
    tell("form_sending");

    void fetch(endpoint, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: new URLSearchParams({
        access_key: key,
        email: clean(said.email.trim()),
        subject: clean(said.subject.trim()),
        message: clean(said.message.trim()),
      }),
    })
      .then((r) => {
        /* Never echo anything the visitor typed back into the page. A
         * "thanks, you said X" confirmation is a stored-XSS vector for
         * free, and the CSP is not what should be catching it. */
        tell(r.ok ? "form_sent" : "form_failed");
        if (!r.ok && button !== null) button.disabled = false;
      })
      .catch(() => {
        tell("form_failed");
        if (button !== null) button.disabled = false;
      });
  });
}

/* ---- opening it -------------------------------------------------------
 * `<dialog>` rather than this page's own overlay pattern, because a form
 * is the one thing here that genuinely traps focus: a reader tabbing out
 * of it into a page they cannot see is lost. `showModal()` gives that,
 * and Escape, and a backdrop, without any of it being written.
 *
 * With no script the dialog is shown inline inside Contact by a rule in
 * the stylesheet — one element, no second copy of the form.
 */
function openTheForm(): void {
  const box = document.querySelector<HTMLDialogElement>("dialog.talk");
  if (!box) return;

  for (const opener of document.querySelectorAll<HTMLElement>("[data-talk]")) {
    opener.addEventListener("click", (ev) => {
      ev.preventDefault();
      box.showModal();
    });
  }

  for (const shut of box.querySelectorAll<HTMLElement>("[data-talk-close]")) {
    shut.addEventListener("click", () => box.close());
  }

  /* The ground around it, as everywhere else on this page. The dialog's
   * own box is what a click lands on when it misses the panel inside. */
  box.addEventListener("click", (ev) => {
    if (ev.target === box) box.close();
  });
}

if (typeof document !== "undefined") {
  document.querySelectorAll<HTMLFormElement>(".contact-form").forEach(wire);
  openTheForm();
}
