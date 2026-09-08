#!/usr/bin/env bash
# Prints the number of always-ready instances the Function App's `http` trigger
# group should be running right now, for
# .github/workflows/functions-always-ready-schedule.yml.
#
# Warm windows, in Europe/London so BST/GMT needs no schedule change:
#   Mon-Fri 17:00-23:00, Sat-Sun 10:00-22:00.
#
# Usage: functions-always-ready-window.sh <count> [mode] [epoch]
#   count  instances to run during a warm window
#   mode   auto (default) | on | off — on and off ignore the windows
#   epoch  "now" as Unix seconds, for scripts/workflow-checks/test-always-ready-window.sh

set -euo pipefail

count="${1:?instance count required}"
mode="${2:-auto}"
now="${3:-$(date +%s)}"

# Warms a window 10 minutes early so it opens on an already-warm instance even
# when GitHub's scheduler fires the job a few minutes late.
LOOKAHEAD_SECONDS=600

in_window() {
  local at="$1" dow hour
  dow="$(TZ=Europe/London date -d "@$at" '+%u')"
  hour="$(TZ=Europe/London date -d "@$at" '+%-H')"

  if [ "$dow" -le 5 ]; then
    [ "$hour" -ge 17 ] && [ "$hour" -lt 23 ]
  else
    [ "$hour" -ge 10 ] && [ "$hour" -lt 22 ]
  fi
}

case "$mode" in
  on)
    echo "$count"
    ;;
  off)
    echo 0
    ;;
  auto)
    if in_window "$now" || in_window "$((now + LOOKAHEAD_SECONDS))"; then
      echo "$count"
    else
      echo 0
    fi
    ;;
  *)
    echo "unknown mode: $mode (expected auto, on, or off)" >&2
    exit 2
    ;;
esac
