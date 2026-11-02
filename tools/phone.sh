#!/usr/bin/env bash
# Put the running preview on an iPhone simulator.
#
#     ./tools/phone.sh            # iPhone 17
#     ./tools/phone.sh "iPhone Air"
#
# Needs ./preview.sh running in another window — this points the
# simulator's Safari at it, it does not build anything.
#
# A simulator is a LAYOUT CHECK. Approval happens on a real phone.
set -euo pipefail
DEVICE="${1:-iPhone 17}"

PORT=$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk '/zola/ {split($9,a,":"); print a[2]; exit}')
if [ -z "${PORT:-}" ]; then
  printf '\n  No preview running. Start ./preview.sh in another window first.\n\n' >&2
  exit 1
fi

xcrun simctl boot "$DEVICE" 2>/dev/null || true
open -a Simulator
# give a cold boot time to reach the home screen before handing it a url
until xcrun simctl openurl "$DEVICE" "http://127.0.0.1:$PORT" 2>/dev/null; do sleep 1; done
printf '\n  %s → http://127.0.0.1:%s\n\n' "$DEVICE" "$PORT"
