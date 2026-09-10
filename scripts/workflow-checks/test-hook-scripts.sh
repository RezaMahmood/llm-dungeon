#!/usr/bin/env bash
# Smoke tests for the workflow guard scripts: .specify/scripts/bash/*.sh and
# bin/wt*. These run on every session (the PreToolUse and SessionStart/
# SessionEnd hooks in .claude/settings.json) or against real worktrees, and
# they are edited from inside the very worktrees they protect — so a syntax
# error or an inverted condition fails open, silently, exactly where nobody
# is looking (issue #293, problem 5).
#
# Everything here runs against throwaway git repositories in $TMPDIR. No
# docker, no gh, no network.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYNC_HOOK="$REPO_ROOT/.specify/scripts/bash/check-worktree-sync.sh"
RETURN_HOOK="$REPO_ROOT/.specify/scripts/bash/return-to-main.sh"

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
echo "check-worktree-sync.sh — container identity vs HEAD (no feature.json)"
repo="$(new_repo sync-basic)"
( cd "$repo" && "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "plain repo, nothing to compare, allows the edit"

( cd "$repo" && WORKTREE_CONTAINER=main "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "container branch matches HEAD"

# The regression that matters: before issue #293 this script exited 0 on the
# missing feature.json above and never reached the container check at all.
( cd "$repo" && WORKTREE_CONTAINER=perf/iframes "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 2 $? "container started for another branch blocks the edit"

git_q -C "$repo" checkout -q --detach
( cd "$repo" && WORKTREE_CONTAINER=main "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 2 $? "detached HEAD inside a worktree container blocks the edit"
git_q -C "$repo" checkout -q main

# Conflict resolution must not be blocked: a rebase onto main is the fix for
# a stale worktree, and it moves HEAD by design.
touch "$repo/.git/MERGE_HEAD"
( cd "$repo" && WORKTREE_CONTAINER=perf/iframes "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "mid-merge, the mismatch check stands down"
rm -f "$repo/.git/MERGE_HEAD"

mkdir -p "$repo/.git/rebase-merge"
( cd "$repo" && WORKTREE_CONTAINER=perf/iframes "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "mid-rebase, the mismatch check stands down"
rm -rf "$repo/.git/rebase-merge"

( cd "$WORKDIR" && WORKTREE_CONTAINER=whatever "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "outside a git repository, no-op"

echo
echo "check-worktree-sync.sh — feature.json expectation vs HEAD"
repo="$(new_repo sync-feature)"
mkdir -p "$repo/.specify"
printf '{"feature_directory": "specs/010-story-test-play"}\n' >"$repo/.specify/feature.json"
( cd "$repo" && "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 2 $? "HEAD is on main but feature.json expects the feature branch"

git_q -C "$repo" checkout -q -b 010-story-test-play
( cd "$repo" && "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "HEAD matches feature.json"

( cd "$repo" && WORKTREE_CONTAINER=010-story-test-play "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "container, HEAD and feature.json all agree"

printf 'not json at all\n' >"$repo/.specify/feature.json"
( cd "$repo" && "$SYNC_HOOK" >/dev/null 2>&1 )
expect_status 0 $? "unparseable feature.json is ignored, not fatal"

echo
echo "return-to-main.sh — SessionEnd returns the primary checkout to main"
repo="$(new_repo return-clean)"
git_q -C "$repo" checkout -q -b perf/slow-page-load
( cd "$repo" && "$RETURN_HOOK" SessionEnd >/dev/null 2>&1 )
expect_equal "main" "$(branch_of "$repo")" "clean tree returns to main"

repo="$(new_repo return-stdin)"
git_q -C "$repo" checkout -q -b perf/slow-page-load
( cd "$repo" && echo '{"hook_event_name":"SessionEnd"}' | "$RETURN_HOOK" >/dev/null 2>&1 )
expect_equal "main" "$(branch_of "$repo")" "event read from the hook's stdin payload"

repo="$(new_repo return-dirty)"
git_q -C "$repo" checkout -q -b perf/slow-page-load
echo "work in progress" >>"$repo/README.md"
( cd "$repo" && "$RETURN_HOOK" SessionEnd >/dev/null 2>&1 )
expect_equal "perf/slow-page-load" "$(branch_of "$repo")" "uncommitted tracked work is never switched away from"

repo="$(new_repo return-rebase)"
git_q -C "$repo" checkout -q -b perf/slow-page-load
mkdir -p "$repo/.git/rebase-merge"
( cd "$repo" && "$RETURN_HOOK" SessionEnd >/dev/null 2>&1 )
expect_equal "perf/slow-page-load" "$(branch_of "$repo")" "an in-progress rebase is left alone"
rm -rf "$repo/.git/rebase-merge"

repo="$(new_repo return-start)"
git_q -C "$repo" checkout -q -b perf/slow-page-load
out="$( cd "$repo" && "$RETURN_HOOK" SessionStart 2>&1 )"
expect_equal "perf/slow-page-load" "$(branch_of "$repo")" "SessionStart reports but never switches"
case "$out" in
  *"not 'main'"*) ok "SessionStart says which branch the checkout is parked on" ;;
  *) bad "SessionStart produced no notice: $out" ;;
esac

repo="$(new_repo return-container)"
git_q -C "$repo" checkout -q -b perf/slow-page-load
( cd "$repo" && WORKTREE_CONTAINER=perf/slow-page-load "$RETURN_HOOK" SessionEnd >/dev/null 2>&1 )
expect_equal "perf/slow-page-load" "$(branch_of "$repo")" "no-op inside a worktree container"

repo="$(new_repo return-worktree)"
git_q -C "$repo" branch -q perf/iframes
git_q -C "$repo" worktree add -q "$repo/.worktrees/perf/iframes" perf/iframes 2>/dev/null
( cd "$repo/.worktrees/perf/iframes" && "$RETURN_HOOK" SessionEnd >/dev/null 2>&1 )
expect_equal "perf/iframes" "$(branch_of "$repo/.worktrees/perf/iframes")" "a linked worktree is left on its own branch"
expect_equal "main" "$(branch_of "$repo")" "and the primary checkout is untouched by it"

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
WORKTREE_CONTAINER=perf/iframes "$REPO_ROOT/bin/wt-prune" >/dev/null 2>&1
expect_status 1 $? "bin/wt-prune refuses to run inside a worktree container"
"$REPO_ROOT/bin/wt-prune" --nonsense >/dev/null 2>&1
expect_status 1 $? "bin/wt-prune rejects unknown options"

"$REPO_ROOT/bin/wt-sync" --help >/dev/null 2>&1
expect_status 0 $? "bin/wt-sync --help"

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
expect_status 2 $? "a worktree three majors behind blocks"

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
expect_equal "0" "$(find "$WT_TEST_LOGS" -mindepth 2 -type f 2>/dev/null | wc -l | tr -d " ")" \
  "run transcripts stay flat (branch slashes are slugged, not nested)"

"$REPO_ROOT/bin/wt" --logs >/dev/null 2>&1
expect_status 0 $? "bin/wt --logs summarises without needing a branch"

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

unset WT_LOG_DIR

echo
echo "$passes passed, $failures failed"
[ "$failures" -eq 0 ]
