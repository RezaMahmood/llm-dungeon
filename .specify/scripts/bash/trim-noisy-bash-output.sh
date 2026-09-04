#!/usr/bin/env bash
# PreToolUse guard for Bash: rewrites known-noisy test/build commands so
# their output is trimmed before it ever lands in context (head+tail,
# middle dropped), instead of being captured and re-sent verbatim on every
# subsequent turn. No-op for anything that isn't recognized as noisy, and
# no-op if the command already limits its own output.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

if [[ -z "$command" ]]; then
  echo '{}'
  exit 0
fi

# Commands whose stdout/stderr is routinely huge: package installs, test
# runners, build tools.
noisy_pattern='(^|[;&|[:space:]])(npm (run|test|ci|install|build)|yarn (test|build|install)|pnpm (test|build|install)|pytest|python3? -m pytest|jest|go (test|build)|cargo (test|build)|make)([[:space:]]|$)'

if ! printf '%s' "$command" | grep -qE "$noisy_pattern"; then
  echo '{}'
  exit 0
fi

# Don't double-wrap a command that already bounds its own output.
if printf '%s' "$command" | grep -qE '\|[[:space:]]*(head|tail|wc)([[:space:]]|$)'; then
  echo '{}'
  exit 0
fi

# Capture to a temp file rather than piping straight into head+tail: head
# can over-read from a live pipe and starve tail, silently dropping the
# tail entirely. A file makes the trim deterministic and preserves the
# original exit code.
wrapped="_tmf=\$(mktemp); { ${command} ; } >\"\$_tmf\" 2>&1; _ec=\$?; _total=\$(wc -l < \"\$_tmf\"); if [ \"\$_total\" -gt 210 ]; then head -n 60 \"\$_tmf\"; echo \"... [trim-noisy-bash-output: \$((_total - 210)) lines trimmed] ...\"; tail -n 150 \"\$_tmf\"; else cat \"\$_tmf\"; fi; rm -f \"\$_tmf\"; exit \$_ec"

jq -n --arg cmd "$wrapped" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    updatedInput: { command: $cmd }
  }
}'
