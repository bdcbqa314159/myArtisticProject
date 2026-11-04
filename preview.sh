#!/usr/bin/env bash
# See the page, on this machine, before anyone else does.
#
#   ./preview.sh          — or double-click preview.command in Finder
#
# Leave it running while you work. Save a text file, drop in an image:
# the page in your browser reloads by itself. Ctrl-C here stops it.
#
# This needs ONE program installed, and it offers to install it for you.
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\n  %s\n' "$*"; }
step() { printf '  %s\n' "$*"; }

say "starting a preview of the page"

# Zola builds the site. The compiled JavaScript is in the repository
# already, so there is no Node and no build step here.
if ! command -v zola >/dev/null 2>&1; then
  step "Zola is not installed yet — it is the program that builds the site."
  if command -v brew >/dev/null 2>&1; then
    step "Installing it now. This happens once and takes about a minute."
    brew install zola
  else
    printf '\n  Homebrew is missing, and it is how Zola gets installed.\n'
    printf '  Paste this into Terminal, press Return, follow what it asks,\n'
    printf '  then run this again.\n\n'
    printf '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n\n'
    exit 1
  fi
fi

# Build once, so a mistake is reported here rather than in silence.
if ! zola build >/tmp/landing-build.txt 2>&1; then
  printf '\n  The site did not build. Zola says:\n\n'
  sed 's/^/    /' /tmp/landing-build.txt
  printf '\n  Nothing is broken on the published site — this is only your copy.\n\n'
  exit 1
fi

PORT=1111
while lsof -i :"$PORT" >/dev/null 2>&1; do PORT=$((PORT + 1)); done

# ---- the studio panel -------------------------------------------------
# Two things, one double-click. The panel shows what is on the site
# without opening a text file; zola serves the site itself. Neither knows
# about the other, which is why either can be closed without taking the
# other down.
#
# It prints its own address because that address carries a one-time
# token: a page open in another tab cannot read it, and so cannot reach
# the panel.
PANEL_PORT=$((PORT + 100))
while lsof -i :"$PANEL_PORT" >/dev/null 2>&1; do PANEL_PORT=$((PANEL_PORT + 1)); done

PANEL_URL=""
if [ -f tools/studio/server.py ]; then
  PANEL_OUT=$(mktemp -t studio)
  python3 tools/studio/server.py "$PANEL_PORT" >"$PANEL_OUT" 2>&1 &
  PANEL_PID=$!
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    PANEL_URL=$(head -n 1 "$PANEL_OUT" 2>/dev/null)
    case "$PANEL_URL" in http*) break ;; esac
    PANEL_URL=""
    sleep 0.3
  done
  # whichever way this shell ends, the panel goes with it
  trap 'kill "$PANEL_PID" 2>/dev/null' EXIT INT TERM
fi

say "Opening http://127.0.0.1:$PORT"
if [ -n "$PANEL_URL" ]; then
  step "And the studio, where you can see everything on the site."
fi
step "The page reloads by itself when you change anything."
step "Press Ctrl-C here to stop."
printf '\n'

(
  sleep 2
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:$PORT"
    [ -n "$PANEL_URL" ] && open "$PANEL_URL"
  fi
) &
zola serve --interface 127.0.0.1 --port "$PORT"
