#!/usr/bin/env bash
# Unit tests for scripts/functions-always-ready-window.sh — the warm-window
# schedule .github/workflows/functions-always-ready-schedule.yml runs on.
# Every case pins "now" to a London wall-clock time, so the window edges and
# both DST switches are exercised without waiting for them.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINDOW_SCRIPT="$SCRIPT_DIR/../functions-always-ready-window.sh"

passes=0
failures=0

epoch_of() { # "YYYY-MM-DD HH:MM" London wall clock -> Unix seconds
  python3 -c '
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

when = datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/London"))
print(int(when.timestamp()))
' "$1"
}

expect() { # <london time> <mode> <expected count> <label>
  local at="$1" mode="$2" want="$3" label="$4" got
  got="$(bash "$WINDOW_SCRIPT" 1 "$mode" "$(epoch_of "$at")")"

  if [ "$got" = "$want" ]; then
    passes=$((passes + 1))
    echo "  ✓ $label ($at, $mode) -> $got"
  else
    failures=$((failures + 1))
    echo "  ✗ $label ($at, $mode) -> $got, expected $want"
  fi
}

echo "Weekday window (Mon-Fri 17:00-23:00)"
expect "2026-09-09 16:00" auto 0 "cold well before the window"
expect "2026-09-09 16:50" auto 1 "warmed by the lookahead"
expect "2026-09-09 17:00" auto 1 "window open"
expect "2026-09-09 22:50" auto 1 "still open at the last run inside it"
expect "2026-09-09 23:00" auto 0 "released on the closing boundary"
expect "2026-09-09 09:00" auto 0 "weekday mornings stay cold"

echo "Weekend window (Sat-Sun 10:00-22:00)"
expect "2026-09-12 09:00" auto 0 "cold well before the window"
expect "2026-09-12 09:50" auto 1 "warmed by the lookahead"
expect "2026-09-12 15:00" auto 1 "window open"
expect "2026-09-12 21:50" auto 1 "still open at the last run inside it"
expect "2026-09-12 22:00" auto 0 "released on the closing boundary"
expect "2026-09-13 22:00" auto 0 "Sunday closes at 22:00 too"

echo "Week edges"
expect "2026-09-11 22:50" auto 1 "Friday runs to 23:00"
expect "2026-09-14 09:50" auto 0 "Monday has no 10:00 window"
expect "2026-09-14 16:50" auto 1 "Monday warms for 17:00"

echo "DST switches (schedule is London-local, not UTC)"
expect "2026-03-29 09:50" auto 1 "Sunday BST begins"
expect "2026-10-25 21:50" auto 1 "Sunday GMT resumes"
expect "2026-10-26 16:50" auto 1 "Monday after GMT resumes"
expect "2026-10-26 23:00" auto 0 "Monday close after GMT resumes"

echo "Manual overrides ignore the windows"
expect "2026-09-09 03:00" on 1 "on outside a window"
expect "2026-09-09 20:00" off 0 "off inside a window"

echo "Unknown mode is rejected"
if bash "$WINDOW_SCRIPT" 1 sometimes "$(epoch_of "2026-09-09 20:00")" >/dev/null 2>&1; then
  failures=$((failures + 1))
  echo "  ✗ unknown mode should exit non-zero"
else
  passes=$((passes + 1))
  echo "  ✓ unknown mode exits non-zero"
fi

echo
echo "$passes passed, $failures failed"
[ "$failures" -eq 0 ]
