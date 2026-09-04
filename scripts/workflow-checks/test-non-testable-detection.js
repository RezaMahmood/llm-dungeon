#!/usr/bin/env node
// Fixture test for specs/023-cicd-pipeline-optimization tasks.md T003.
//
// Exercises check-non-testable.mjs — the actual implementation
// .github/actions/detect-non-testable-changes/action.yml runs in CI —
// rather than a separate reimplementation of its logic. That pattern list
// is the actual product decision (FR-019/FR-020) this test guards.
//
// Run with: node scripts/workflow-checks/test-non-testable-detection.js

import { allNonTestable } from "./check-non-testable.mjs";

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

check(
  "a single specs/**/*.md file alone -> all-non-testable = true " +
    "(regression check for #165 Scenario 6: this exact shape previously " +
    "evaluated false under dorny/paths-filter's predicate-quantifier: every)",
  allNonTestable(["specs/023-cicd-pipeline-optimization/quickstart.md"]) === true
);

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures > 0 ? 1 : 0);
