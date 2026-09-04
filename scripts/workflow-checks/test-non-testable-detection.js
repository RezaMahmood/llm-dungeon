#!/usr/bin/env node
// Fixture test for specs/023-cicd-pipeline-optimization tasks.md T003.
//
// .github/actions/detect-non-testable-changes/action.yml delegates its
// glob evaluation to dorny/paths-filter with predicate-quantifier: "every"
// against the pattern list below. That pattern list is the actual product
// decision (FR-019/FR-020) this test guards — dorny/paths-filter's own
// matching engine is third-party and out of scope to re-test here. This
// file re-implements the same "every changed file matches one of these
// patterns" semantics with micromatch (a gitignore-style glob matcher) so
// the pattern list itself can be exercised locally, in CI, with no GitHub
// Actions runtime required.
//
// Run with: node scripts/workflow-checks/test-non-testable-detection.js

import mm from "micromatch";

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

// Must stay byte-identical to the `non_testable` filter in
// .github/actions/detect-non-testable-changes/action.yml.
const NON_TESTABLE_PATTERNS = [
  "**/*.md",
  "specs/**",
  "docs/**",
  "LICENSE",
  "LICENSE.*",
  "CONTRIBUTING.md",
];

function allNonTestable(changedFiles) {
  // predicate-quantifier: "every" — true iff every file matches at least
  // one non-testable pattern.
  return changedFiles.every((f) => mm.isMatch(f, NON_TESTABLE_PATTERNS, { dot: true }));
}

console.log("=== Non-testable-change detection fixture tests ===\n");

check(
  "all-docs change set -> all-non-testable = true",
  allNonTestable(["specs/023-cicd-pipeline-optimization/spec.md", "docs/INFRASTRUCTURE.md", "README.md"]) === true
);

check(
  "all-code change set -> all-non-testable = false",
  allNonTestable(["src/backend/app.py", "src/frontend/src/App.tsx"]) === false
);

check(
  "mixed docs+code change set -> all-non-testable = false",
  allNonTestable(["specs/023-cicd-pipeline-optimization/spec.md", "src/backend/app.py"]) === false
);

check(
  "a single testable file among many docs files -> all-non-testable = false",
  allNonTestable([
    "specs/a.md",
    "specs/b.md",
    "docs/c.md",
    "infrastructure/terraform/main.tf",
  ]) === false
);

check(
  "a docs file sitting INSIDE a component directory, alone -> still all-non-testable = true " +
    "(content-type based, not location-based, per the clarification session)",
  allNonTestable(["src/frontend/README.md"]) === true
);

check(
  "a docs file inside a component directory PLUS a code file in that same directory -> false",
  allNonTestable(["src/frontend/README.md", "src/frontend/src/App.tsx"]) === false
);

check(
  "LICENSE and CONTRIBUTING.md alone -> all-non-testable = true",
  allNonTestable(["LICENSE", "CONTRIBUTING.md"]) === true
);

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures > 0 ? 1 : 0);
