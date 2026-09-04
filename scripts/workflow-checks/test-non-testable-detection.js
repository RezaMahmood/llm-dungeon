#!/usr/bin/env node
// Fixture test for specs/023-cicd-pipeline-optimization tasks.md T003.
//
// Exercises check-non-testable.mjs — the actual implementation
// .github/actions/detect-non-testable-changes/action.yml runs in CI —
// rather than a separate reimplementation of its logic. That pattern list
// is the actual product decision (FR-019/FR-020) this test guards.
//
// Run with: node scripts/workflow-checks/test-non-testable-detection.js

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { allNonTestable } from "./check-non-testable.mjs";

const CHECK_SCRIPT = fileURLToPath(new URL("./check-non-testable.mjs", import.meta.url));

// Invokes the module the exact way detect-non-testable-changes/action.yml
// does: as a child process, changed files passed via CHANGED_FILES_JSON.
// The imported allNonTestable() checks above only prove the predicate
// logic is right; they can't catch a broken CLI entry point (the import
// path is never exercised when the module is run as a subprocess) — which
// is exactly what shipped in this PR's first revision (Copilot review,
// PR #199): a hand-rolled `file://${process.argv[1]}` comparison that
// only happens to match when argv[1] resolves to a plain absolute path
// with no symlinks/encoding involved.
function cliAllNonTestable(changedFiles) {
  const output = execFileSync("node", [CHECK_SCRIPT], {
    env: { ...process.env, CHANGED_FILES_JSON: JSON.stringify(changedFiles) },
    encoding: "utf8",
  }).trim();
  if (output !== "true" && output !== "false") {
    throw new Error(`check-non-testable.mjs CLI printed unexpected output: ${JSON.stringify(output)}`);
  }
  return output === "true";
}

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

check(
  "CLI entry point (invoked as a subprocess, exactly like action.yml does) -> all-non-testable = true for docs-only",
  cliAllNonTestable(["specs/023-cicd-pipeline-optimization/quickstart.md"]) === true
);

check(
  "CLI entry point -> all-non-testable = false for a code change",
  cliAllNonTestable(["src/backend/app.py"]) === false
);

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures > 0 ? 1 : 0);
