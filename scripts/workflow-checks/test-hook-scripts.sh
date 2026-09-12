#!/usr/bin/env bash
# Smoke tests for the workflow scripts: .specify/scripts/bash/*.sh and
# bin/wt*. These run from session hooks in .claude/settings.json or against
# real worktrees, so a syntax error or an inverted condition fails silently,
# exactly where nobody is looking (issue #293, problem 5).
#
# Everything here runs against throwaway git repositories in $TMPDIR. No
# docker, no gh, no network.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

passes=0
failures=0
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

ok()   { passes=$((passes + 1)); echo "  ✓ $1"; }
bad()  { failures=$((failures + 1)); echo "  ✗ $1"; }

expect_status() { # <expected> <actual> <label>
  if [ "$1" = "$2" ]; then ok "$3 (exit $2)"; else bad "$3 — exit $2, expected $1"; fi
}

expect_equal() { # <expected> <actual> <label>
  if [ "$1" = "$2" ]; then ok "$3 ($2)"; else bad "$3 — got '$2', expected '$1'"; fi
}

git_q() { git -c user.email=test@example.com -c user.name=Test -c commit.gpgsign=false "$@"; }

new_repo() { # <name> -> prints path to a repo with one commit on main
  local dir="$WORKDIR/$1"
  mkdir -p "$dir"
  git_q -C "$dir" init -q -b main
  echo "seed" >"$dir/README.md"
  # Same as the real repo: worktrees live inside the checkout but are never
  # tracked by it, so a fixture's `git add -A` does not try to embed one.
  echo ".worktrees/" >"$dir/.gitignore"
  git_q -C "$dir" add -A
  git_q -C "$dir" commit -q -m "init"
  echo "$dir"
}

branch_of() { git -C "$1" rev-parse --abbrev-ref HEAD 2>/dev/null; }

echo "Static syntax check (bash -n)"
for f in "$REPO_ROOT"/.specify/scripts/bash/*.sh "$REPO_ROOT"/bin/wt "$REPO_ROOT"/bin/wt-prune "$REPO_ROOT"/bin/wt-sync; do
  if bash -n "$f" 2>/dev/null; then
    ok "parses: ${f#"$REPO_ROOT"/}"
  else
    bad "syntax error: ${f#"$REPO_ROOT"/}"
  fi
done

for f in "$REPO_ROOT"/.specify/scripts/bash/*.sh "$REPO_ROOT"/bin/wt "$REPO_ROOT"/bin/wt-prune "$REPO_ROOT"/bin/wt-sync; do
  [ -x "$f" ] || bad "not executable: ${f#"$REPO_ROOT"/}"
done

echo
echo "bin/wt* — argument handling and refusals"
# bin/wt writes its run log to <primary checkout>/.wt-logs by default. Point
# it at a throwaway directory so exercising the refusals here never appends
# to the real repository's diagnostics.
WT_TEST_LOGS="$WORKDIR/wt-logs"
export WT_LOG_DIR="$WT_TEST_LOGS"

"$REPO_ROOT/bin/wt" --help >/dev/null 2>&1
expect_status 0 $? "bin/wt --help"
"$REPO_ROOT/bin/wt" main >/dev/null 2>&1
expect_status 1 $? "bin/wt refuses to make a worktree for the trunk"
"$REPO_ROOT/bin/wt" >/dev/null 2>&1
expect_status 1 $? "bin/wt with no branch"
"$REPO_ROOT/bin/wt" --nonsense >/dev/null 2>&1
expect_status 1 $? "bin/wt rejects unknown options"

"$REPO_ROOT/bin/wt-prune" --help >/dev/null 2>&1
expect_status 0 $? "bin/wt-prune --help"
# Refuses on WHERE it is run, not on WORKTREE_CONTAINER: that variable is
# set for host sessions too now, so refusing on it would reject a user
# standing in the primary checkout who had already done what the message
# asked. A linked worktree is the thing that cannot see its siblings.
repo="$(new_repo prune-location)"
git_q -C "$repo" worktree add -q -b chore/elsewhere "$repo/.worktrees/chore/elsewhere" >/dev/null 2>&1
prune_out="$WORKDIR/prune-location.out"
( cd "$repo/.worktrees/chore/elsewhere" && "$REPO_ROOT/bin/wt-prune" ) >"$prune_out" 2>&1
expect_status 1 $? "bin/wt-prune refuses to run from inside a worktree"
if grep -q "Refusing to run from the worktree" "$prune_out"; then
  ok "...naming the location as the reason, not an environment variable"
else
  bad "...but did not refuse on location"
fi
# The inherited variable alone must NOT be what refuses: standing in the
# primary checkout is the supported way to run this, and a host session
# leaves WORKTREE_CONTAINER set in any shell spawned from it.
prune_env_out="$WORKDIR/prune-env.out"
( cd "$repo" && WORKTREE_CONTAINER=chore/elsewhere "$REPO_ROOT/bin/wt-prune" ) >"$prune_env_out" 2>&1
if grep -q "Refusing to run from the worktree" "$prune_env_out"; then
  bad "an inherited WORKTREE_CONTAINER wrongly blocks wt-prune in the primary checkout"
else
  ok "an inherited WORKTREE_CONTAINER does not block wt-prune in the primary checkout"
fi
"$REPO_ROOT/bin/wt-prune" --nonsense >/dev/null 2>&1
expect_status 1 $? "bin/wt-prune rejects unknown options"

"$REPO_ROOT/bin/wt-sync" --help >/dev/null 2>&1
expect_status 0 $? "bin/wt-sync --help"

# Deliberately run inside a fixture, not $REPO_ROOT: if this refusal ever
# regressed, --no-container skips the Docker preflight, and the run would
# create a real branch and worktree in the developer's own checkout and
# then sit on an interactive `claude` -- the suite would hang rather than
# report a failure. Every other bin/wt case that can get past preflight
# uses new_repo for the same reason.
repo="$(new_repo flag-conflict)"
( cd "$repo" && "$REPO_ROOT/bin/wt" chore/conflict --no-container --rebuild ) >/dev/null 2>&1 </dev/null
expect_status 1 $? "bin/wt refuses --no-container together with --rebuild"
if grep -q '"code":"E_FLAG_CONFLICT"' "$WT_TEST_LOGS/events.jsonl" 2>/dev/null; then
  ok "...and the refusal reaches the log, like every other refusal"
else
  bad "...but the refusal was never logged, so bin/wt --logs cannot see it"
fi

echo
echo "bin/wt --no-container — host sessions for non-spec branches"
# The whole point of this mode is that it needs no Docker and no
# devcontainer CLI, so it has to be exercisable exactly here, in the suite
# that promises "no docker, no gh, no network". --shell is used rather than
# the default claude mode so the test does not require the Claude Code CLI
# on the host either; both modes take the same path to get there.
repo="$(new_repo host-session)"
host_out="$WORKDIR/host-session.out"
printf 'printf "PWD=%%s\\n" "$PWD"; printf "WTC=%%s\\n" "$WORKTREE_CONTAINER"; printf "HEAD=%%s\\n" "$(git rev-parse --abbrev-ref HEAD)"\n' \
  | ( cd "$repo" && "$REPO_ROOT/bin/wt" chore/host-demo --no-container --shell ) >"$host_out" 2>&1
expect_status 0 $? "a non-spec branch starts a host session"

# Compared against the physical path: on macOS $TMPDIR is /var/..., a
# symlink to /private/var/..., and the session's own $PWD is the resolved
# form. Comparing the two spellings fails on a difference that is not one.
repo_real="$(cd "$repo" && pwd -P)"
expect_equal "$repo_real/.worktrees/chore/host-demo" \
  "$(sed -n 's/^PWD=//p' "$host_out" | tail -1)" \
  "the session runs with its cwd inside that branch's worktree"

# WORKTREE_CONTAINER names the branch the session was started for; wt-prune
# and the container label read it, and it is the session's own breadcrumb.
expect_equal "chore/host-demo" \
  "$(sed -n 's/^WTC=//p' "$host_out" | tail -1)" \
  "the host session exports WORKTREE_CONTAINER"

expect_equal "chore/host-demo" \
  "$(sed -n 's/^HEAD=//p' "$host_out" | tail -1)" \
  "the worktree is on the branch it is named for"

expect_equal "chore/host-demo" "$(branch_of "$repo/.worktrees/chore/host-demo")" \
  "...and still is after the session ends"

expect_equal "main" "$(branch_of "$repo")" \
  "the primary checkout is left on main, not moved to the new branch"

# A spec branch is no longer forced into a container: the constitution
# leaves that choice to whoever starts the session, so --no-container has
# to work here exactly as it does for chore/*.
repo="$(new_repo host-session-newspec)"
mkdir -p "$repo/.specify"
echo "speckit" >"$repo/.specify/README.md"
git_q -C "$repo" add -A
git_q -C "$repo" commit -q -m "add .specify"
newspec_out="$WORKDIR/host-session-newspec.out"
printf 'printf "HEAD=%%s\\n" "$(git rev-parse --abbrev-ref HEAD)"\n' \
  | ( cd "$repo" && "$REPO_ROOT/bin/wt" 028-brand-new --no-container --shell ) >"$newspec_out" 2>&1
expect_status 0 $? "a spec-numbered branch may run --no-container"
expect_equal "028-brand-new" "$(branch_of "$repo/.worktrees/028-brand-new")" \
  "...in a worktree on its own branch"

# The feature pointer is still bootstrapped for a spec branch, container or
# not: it is what the speckit commands resolve the active feature from.
if grep -q '"feature_directory": "specs/028-brand-new"' \
    "$repo/.worktrees/028-brand-new/.specify/feature.json" 2>/dev/null; then
  ok "...with .specify/feature.json pointing at its spec folder"
else
  bad "...but .specify/feature.json was not bootstrapped"
fi

echo
echo "bin/wt-prune — worktree directory must spell out the branch name"
if command -v gh >/dev/null 2>&1; then
  repo="$(new_repo prune-naming)"
  git_q -C "$repo" branch -q docs/overview
  git_q -C "$repo" branch -q perf/iframes
  # Correct: a slashed branch nests, so docs/overview lives at
  # .worktrees/docs/overview -- its basename alone never matches the branch.
  git_q -C "$repo" worktree add -q "$repo/.worktrees/docs/overview" docs/overview 2>/dev/null
  git_q -C "$repo" worktree add -q "$repo/.worktrees/wrong-name" perf/iframes 2>/dev/null
  # No remote here, so `gh pr list` fails and every branch reads as "no PR" --
  # which is what we want: nothing is prunable, only the naming is asserted.
  out="$( cd "$repo" && "$REPO_ROOT/bin/wt-prune" 2>&1 )"
  case "$out" in
    *"docs/overview (in mismatched"*) bad "a nested slashed branch name was misreported as mismatched" ;;
    *) ok "docs/overview at .worktrees/docs/overview is not flagged" ;;
  esac
  case "$out" in
    *"perf/iframes (in mismatched directory .worktrees/wrong-name)"*) ok "a genuinely misnamed directory is reported" ;;
    *) bad "expected the wrong-name worktree to be flagged: $out" ;;
  esac
  case "$out" in
    *"0 would be pruned"*) ok "dry run deletes nothing" ;;
    *) bad "expected a dry-run summary with nothing pruned: $out" ;;
  esac
else
  echo "  - skipped: gh is not on PATH"
fi

echo
echo "bin/wt-sync — constitution staleness"
# Mirrors what issue #293 found live: a worktree branched off an older main
# and never rebased, so it is still governed by a constitution three majors
# out of date while main has moved on.
repo="$(new_repo sync-governance)"
mkdir -p "$repo/.specify/memory"
printf '**Version**: 3.1.0 | **Ratified**: 2026-08-28\n' >"$repo/.specify/memory/constitution.md"
echo "CLAUDE.md as it was then" >"$repo/CLAUDE.md"
git_q -C "$repo" add -A
git_q -C "$repo" commit -q -m "constitution v3.1.0"
git_q -C "$repo" branch -q issue/275
git_q -C "$repo" worktree add -q "$repo/.worktrees/issue/275" issue/275 2>/dev/null
printf '**Version**: 6.0.0 | **Ratified**: 2026-08-28\n' >"$repo/.specify/memory/constitution.md"
echo "CLAUDE.md as it is now" >"$repo/CLAUDE.md"
git_q -C "$repo" add -A
git_q -C "$repo" commit -q -m "constitution v6.0.0"
( cd "$repo" && "$REPO_ROOT/bin/wt-sync" --ref=main >/dev/null 2>&1 )
expect_status 2 $? "a worktree three majors behind is reported"

out="$( cd "$repo" && "$REPO_ROOT/bin/wt-sync" --ref=main 2>&1 )"
case "$out" in
  *"CLAUDE.md"*) ok "stale bootstrap files landed on the ref are listed" ;;
  *) bad "expected CLAUDE.md in the stale list: $out" ;;
esac

git_q -C "$repo/.worktrees/issue/275" rebase main >/dev/null 2>&1
( cd "$repo" && "$REPO_ROOT/bin/wt-sync" --ref=main >/dev/null 2>&1 )
expect_status 0 $? "after rebasing onto the ref, nothing blocks"

repo="$(new_repo sync-empty)"
( cd "$repo" && "$REPO_ROOT/bin/wt-sync" --ref=main >/dev/null 2>&1 )
expect_status 0 $? "no worktrees at all"

echo
echo "bin/wt — run logging"
# The whole point of the log is to still be readable after the terminal has
# scrolled away, so these assert on the file, not on what was printed.
expect_equal "yes" "$([ -f "$WT_TEST_LOGS/events.jsonl" ] && echo yes || echo no)" \
  "a refused run still records an event"

case "$(cat "$WT_TEST_LOGS/events.jsonl")" in
  *'"code":"E_TRUNK_BRANCH"'*) ok "the trunk refusal is recorded under its own error code" ;;
  *) bad "expected E_TRUNK_BRANCH in events.jsonl" ;;
esac

case "$(cat "$WT_TEST_LOGS/events.jsonl")" in
  *'"code":"OK_START"'*) ok "each run records where it started" ;;
  *) bad "expected OK_START in events.jsonl" ;;
esac

# Every line must be a self-contained JSON object: the file is append-only
# from several runs at once, so anything else makes the whole log unreadable.
if command -v jq >/dev/null 2>&1; then
  if jq -e -c . "$WT_TEST_LOGS/events.jsonl" >/dev/null 2>&1; then
    ok "every events.jsonl line is valid JSON"
  else
    bad "events.jsonl contains a line that is not valid JSON"
  fi
else
  ok "events.jsonl JSON validity (skipped — no jq)"
fi

# A branch name with a slash must not create a directory inside the log dir.
# This needs a run that actually reaches log setup with a slashed branch: the
# refusals above all use "main". Trimming PATH to the system directories drops
# the devcontainer CLI, so the run stops at E_NO_DEVCONTAINER_CLI -- after
# logging is initialised, and before anything touches git or docker.
SLUG_LOGS="$WORKDIR/wt-logs-slug"
( PATH="/usr/bin:/bin:/usr/sbin:/sbin" WT_LOG_DIR="$SLUG_LOGS" \
    "$REPO_ROOT/bin/wt" perf/some-branch >/dev/null 2>&1 )
expect_equal "0" "$(find "$SLUG_LOGS" -mindepth 2 -type f 2>/dev/null | wc -l | tr -d " ")" \
  "run transcripts stay flat (branch slashes are slugged, not nested)"
expect_equal "1" "$(find "$SLUG_LOGS" -maxdepth 1 -name "run-perf-some-branch-*.log" 2>/dev/null | wc -l | tr -d " ")" \
  "the slashed branch name reaches the transcript filename as a slug"

"$REPO_ROOT/bin/wt" --logs >/dev/null 2>&1
expect_status 0 $? "bin/wt --logs summarises without needing a branch"
"$REPO_ROOT/bin/wt" --logs 5 >/dev/null 2>&1
expect_status 0 $? "bin/wt --logs <count>"

# Positionals are resolved after the whole argument loop, so a bare word means
# the same thing wherever it sits. Both of these used to print a summary and
# exit 0, silently dropping the branch the caller asked to start a session on.
"$REPO_ROOT/bin/wt" some-branch --logs >/dev/null 2>&1
expect_status 1 $? "bin/wt <branch> --logs is refused, not silently summarised"
out="$("$REPO_ROOT/bin/wt" some-branch --logs 2>&1)"
case "$out" in
  *"takes no branch name"*) ok "...and says which of the two was meant" ;;
  *) bad "expected a branch-vs-count explanation, got: $out" ;;
esac
"$REPO_ROOT/bin/wt" 5 --logs >/dev/null 2>&1
expect_status 0 $? "a count before --logs means the same as after it"
"$REPO_ROOT/bin/wt" one two >/dev/null 2>&1
expect_status 1 $? "bin/wt rejects two branches"

out="$("$REPO_ROOT/bin/wt" --logs 2>&1)"
case "$out" in
  *E_TRUNK_BRANCH*) ok "--logs groups past failures by error code" ;;
  *) bad "expected E_TRUNK_BRANCH in the --logs summary: $out" ;;
esac

WT_NO_LOG_DIR="$WORKDIR/wt-logs-disabled"
WT_NO_LOG=1 WT_LOG_DIR="$WT_NO_LOG_DIR" "$REPO_ROOT/bin/wt" main >/dev/null 2>&1
expect_equal "no" "$([ -d "$WT_NO_LOG_DIR" ] && echo yes || echo no)" \
  "WT_NO_LOG=1 writes nothing at all"

# Logging is a diagnostic, never a gate: an unwritable log directory must
# not be the reason a session refuses to start.
out="$(WT_LOG_DIR=/dev/null/nope "$REPO_ROOT/bin/wt" main 2>&1)"
case "$out" in
  *"it's the trunk"*) ok "an unwritable log directory degrades quietly" ;;
  *) bad "expected the normal trunk refusal with an unwritable log dir: $out" ;;
esac

# The reachable version of that: a directory that exists and is writable to
# `mkdir -p` (which succeeds on any existing directory) but not to the file
# write inside it. That is the case where LOG_ENABLED goes to 0 while RUN_LOG
# would otherwise stay set, and a later `tee -a` failure gets misreported as
# the git command failing. Root ignores mode bits, so skip it there.
if [ "$(id -u)" != "0" ]; then
  LOCKED_LOGS="$WORKDIR/wt-logs-locked"
  mkdir -p "$LOCKED_LOGS"
  chmod 500 "$LOCKED_LOGS"
  out="$(WT_LOG_DIR="$LOCKED_LOGS" "$REPO_ROOT/bin/wt" main 2>&1)"
  status=$?
  chmod 700 "$LOCKED_LOGS"
  expect_status 1 $status "an existing but unwritable log directory still refuses the trunk normally"
  case "$out" in
    *"it's the trunk"*) ok "...and reports the real reason, not a logging failure" ;;
    *) bad "expected the trunk refusal, got: $out" ;;
  esac
else
  ok "unwritable existing log directory (skipped — running as root)"
fi

unset WT_LOG_DIR

echo
echo "$passes passed, $failures failed"
[ "$failures" -eq 0 ]
