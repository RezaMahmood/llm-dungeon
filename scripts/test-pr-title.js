#!/usr/bin/env node
// PR-title format unit test for specs/023-cicd-pipeline-optimization
// User Story 4 (tasks.md T023).
//
// Unlike T006/T014 (which test behavior that didn't exist yet), this
// tests scripts/pr-title-config.js's pattern directly — there's no
// meaningful "red" state for a unit test against a module written
// alongside it. The actual TDD "red" state this feature cares about is
// at the workflow level: before T024 wires pr-title-check.yml as a
// required check, a malformed title CAN merge; after, it can't. This
// test's job is to make sure the pattern .github/workflows/
// pr-title-check.yml is configured with (via scripts/pr-title-config.js's
// TYPES/SCOPES, mirrored into the action's `types`/`scopes` inputs) is
// itself correct, so the two can never silently drift apart.
//
// Run with: node scripts/test-pr-title.js

import { validatePrTitle } from "./pr-title-config.js";

let failures = 0;
let passes = 0;

function check(label, condition) {
  if (condition) {
    passes += 1;
    console.log(`  ✓ ${label}`);
  } else {
    failures += 1;
    console.error(`  ✗ ${label}`);
  }
}

console.log("Known-good titles:");
[
  "fix(backend): correct typo in error message",
  "feat(frontend): add adventure select screen",
  "chore(deps-dev): bump vitest from 4.1.10 to 4.1.11",
  "chore(specs): mark 021-npm-dependency-audit as done",
  "fix(infra)!: rotate the storage account key rotation policy",
].forEach((title) => check(`"${title}" is accepted`, validatePrTitle(title)));

console.log("\nKnown-bad titles:");
[
  ["no type or scope at all", "updated the login typo"],
  ["missing scope entirely", "fix: correct typo in error message"],
  ["unrecognized type", "feature(frontend): add adventure select screen"],
  ["unrecognized scope", "fix(billing): correct typo in error message"],
  ["empty description", "fix(backend): "],
  ["scope not lowercase", "fix(Backend): correct typo"],
].forEach(([label, title]) =>
  check(`"${title}" (${label}) is rejected`, !validatePrTitle(title))
);

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures > 0 ? 1 : 0);
