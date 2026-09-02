#!/usr/bin/env node
// Workflow-structure assertion tests for specs/023-cicd-pipeline-optimization
// (CI/CD Pipeline Optimization — Test-on-Push, Build-on-Merge, Manual Deploy).
//
// Static YAML-shape checks that `actionlint` alone does not perform (it
// only checks syntax/schema, not job/step content). Run with:
//   node scripts/test-workflow-structure.js
//
// Exits non-zero on any failure, printing every assertion's pass/fail so
// a human or CI log can see exactly which story's guarantee broke.

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import yaml from "js-yaml";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const WORKFLOWS_DIR = path.join(REPO_ROOT, ".github", "workflows");

let failures = 0;
let passes = 0;

function loadWorkflow(name) {
  const filePath = path.join(WORKFLOWS_DIR, name);
  const raw = fs.readFileSync(filePath, "utf8");
  // js-yaml treats a bare `on:` key as the boolean `true` key under
  // YAML 1.1 rules; workflow files always intend the string "on".
  return yaml.load(raw, { schema: yaml.DEFAULT_SCHEMA });
}

function triggersOf(workflow) {
  // yaml.load parses YAML's `on:` key as boolean `true` (YAML 1.1 core
  // schema quirk) unless quoted in the source; GitHub Actions workflow
  // files never quote it, so read both keys defensively.
  const raw = workflow.on !== undefined ? workflow.on : workflow[true];
  if (raw === undefined || raw === null) return {};
  if (typeof raw === "string") return { [raw]: null };
  if (Array.isArray(raw)) return Object.fromEntries(raw.map((k) => [k, null]));
  return raw;
}

function check(label, condition) {
  if (condition) {
    passes += 1;
    console.log(`  ✓ ${label}`);
  } else {
    failures += 1;
    console.error(`  ✗ ${label}`);
  }
}

function stepsOf(job) {
  return Array.isArray(job && job.steps) ? job.steps : [];
}

function findStepUsing(steps, actionSubstring) {
  return steps.find((s) => typeof s.uses === "string" && s.uses.includes(actionSubstring));
}

function stepRunContains(steps, substring) {
  return steps.some((s) => typeof s.run === "string" && s.run.includes(substring));
}

function findStepById(steps, id) {
  return steps.find((s) => s.id === id);
}

// ---------------------------------------------------------------------
// User Story 1 — test-on-push, merge gate, non-testable-change skip
// ---------------------------------------------------------------------
function testUserStory1() {
  console.log("User Story 1 — test-on-push and non-testable-change skip:");

  const test = loadWorkflow("test.yml");
  const triggers = triggersOf(test);
  check("test.yml has a 'push' trigger", Object.prototype.hasOwnProperty.call(triggers, "push"));
  check(
    "test.yml has a 'pull_request' trigger",
    Object.prototype.hasOwnProperty.call(triggers, "pull_request")
  );

  const changesJob = test.jobs && test.jobs.changes;
  check("test.yml has a 'changes' job", !!changesJob);
  if (changesJob) {
    check(
      "'changes' job uses the shared detect-non-testable-changes action",
      !!findStepUsing(stepsOf(changesJob), "./.github/actions/detect-non-testable-changes")
    );
    check(
      "'changes' job exposes an 'all-non-testable' output",
      !!(changesJob.outputs && changesJob.outputs["all-non-testable"])
    );
  }

  const testJob = test.jobs && test.jobs.test;
  check(
    "'test' job is conditioned on all-non-testable != 'true'",
    !!testJob && typeof testJob.if === "string" && testJob.if.includes("all-non-testable")
  );
  const frontendTestJob = test.jobs && test.jobs["frontend-test"];
  check(
    "'frontend-test' job is conditioned on all-non-testable != 'true'",
    !!frontendTestJob && typeof frontendTestJob.if === "string" && frontendTestJob.if.includes("all-non-testable")
  );
}

// ---------------------------------------------------------------------
// User Story 2 — CI build workflows: no deploy job, workflow_call-only
// reusable builds, idempotent build-skip-if-cached
// ---------------------------------------------------------------------
function testUserStory2() {
  console.log("\nUser Story 2 — build/version/cache-on-merge, no deploy, idempotent:");

  for (const name of ["frontend-build.yml", "backend-build.yml", "infrastructure-build.yml"]) {
    const wf = loadWorkflow(name);
    const jobNames = Object.keys(wf.jobs || {});
    check(
      `${name} has no 'deploy' or 'apply' job`,
      !jobNames.includes("deploy") && !jobNames.includes("apply")
    );
    const triggers = triggersOf(wf);
    check(`${name} has a 'push' trigger`, Object.prototype.hasOwnProperty.call(triggers, "push"));
    check(
      `${name} has no 'workflow_dispatch' trigger`,
      !Object.prototype.hasOwnProperty.call(triggers, "workflow_dispatch")
    );
  }

  for (const name of ["_build-frontend.yml", "_build-backend.yml", "_build-infrastructure.yml"]) {
    const wf = loadWorkflow(name);
    const triggers = triggersOf(wf);
    const triggerKeys = Object.keys(triggers);
    check(
      `${name} declares 'workflow_call' as its only trigger`,
      triggerKeys.length === 1 && triggerKeys[0] === "workflow_call"
    );

    const buildJob = wf.jobs && wf.jobs.build;
    check(`${name} has a 'build' job`, !!buildJob);
    if (buildJob) {
      const steps = stepsOf(buildJob);
      const checkStep = findStepById(steps, "check-artifact");
      check(
        `${name} checks for an existing cached artifact before building (step id 'check-artifact')`,
        !!checkStep
      );
      // The idempotency guarantee (FR-008/SC-006): steps that actually do
      // the build/package work must be gated on that check step's output
      // being false, so a second invocation for an already-cached version
      // short-circuits rather than re-building.
      const gatedSteps = steps.filter(
        (s) =>
          typeof s.if === "string" &&
          s.if.includes("check-artifact") &&
          s.if.includes("artifact_exists") &&
          s.name !== (checkStep && checkStep.name)
      );
      check(
        `${name} gates its build/package steps on check-artifact.outputs.artifact_exists`,
        gatedSteps.length > 0
      );
    }
  }
}

// ---------------------------------------------------------------------
// User Story 3 — CD workflows: workflow_dispatch-only, version input,
// approval-gate asymmetry, no rebuild in deploy/apply
// ---------------------------------------------------------------------
function testUserStory3() {
  console.log("\nUser Story 3 — deploy is explicitly-triggered only, approval-gate asymmetry:");

  const deployWorkflows = ["frontend-deploy.yml", "backend-deploy.yml", "infrastructure-deploy.yml"];

  for (const name of deployWorkflows) {
    const wf = loadWorkflow(name);
    const triggers = triggersOf(wf);
    check(
      `${name} has no 'push' trigger`,
      !Object.prototype.hasOwnProperty.call(triggers, "push")
    );
    check(
      `${name} has no 'pull_request' trigger`,
      !Object.prototype.hasOwnProperty.call(triggers, "pull_request")
    );
    check(
      `${name} declares a 'workflow_dispatch' trigger with a 'version' input`,
      !!triggers.workflow_dispatch &&
        !!triggers.workflow_dispatch.inputs &&
        !!triggers.workflow_dispatch.inputs.version
    );

    const finalJob = (wf.jobs && (wf.jobs.deploy || wf.jobs.apply)) || null;
    check(`${name} has a 'deploy' or 'apply' job`, !!finalJob);
    if (finalJob) {
      const steps = stepsOf(finalJob);
      const hasInstallOrBuild =
        stepRunContains(steps, "npm install") ||
        stepRunContains(steps, "npm ci") ||
        stepRunContains(steps, "npm run build") ||
        stepRunContains(steps, "pip install") ||
        stepRunContains(steps, "terraform plan");
      check(
        `${name}'s deploy/apply job has no install/build/plan step (only download + deploy/apply)`,
        !hasInstallOrBuild
      );
      check(
        `${name}'s deploy/apply job downloads an artifact`,
        !!findStepUsing(steps, "actions/download-artifact")
      );
    }
  }

  const infraApply = loadWorkflow("infrastructure-deploy.yml").jobs.apply;
  check(
    "infrastructure-deploy.yml's apply job targets environment: production-infra",
    !!infraApply && infraApply.environment === "production-infra"
  );

  for (const name of ["frontend-deploy.yml", "backend-deploy.yml"]) {
    const deployJob = loadWorkflow(name).jobs.deploy;
    check(
      `${name}'s deploy job does NOT target an approval-gated environment`,
      !!deployJob && deployJob.environment !== "production-infra"
    );
  }
}

// ---------------------------------------------------------------------
// User Story 4 — version resolution: resolve-version before ensure-
// artifact, explicit not-found version fails with no fallback
// ---------------------------------------------------------------------
function testUserStory4() {
  console.log("\nUser Story 4 — resolve-version and not-found failure path:");

  for (const name of ["frontend-deploy.yml", "backend-deploy.yml", "infrastructure-deploy.yml"]) {
    const wf = loadWorkflow(name);
    const resolveJob = wf.jobs && wf.jobs["resolve-version"];
    check(`${name} has a 'resolve-version' job`, !!resolveJob);

    const jobOrder = Object.keys(wf.jobs || {});
    const ensureIdx = jobOrder.indexOf("ensure-artifact");
    const resolveIdx = jobOrder.indexOf("resolve-version");
    check(
      `${name}'s 'resolve-version' job is declared before 'ensure-artifact'`,
      resolveIdx !== -1 && ensureIdx !== -1 && resolveIdx < ensureIdx
    );

    if (resolveJob) {
      const steps = stepsOf(resolveJob);
      const hasFailurePath = steps.some(
        (s) =>
          typeof s.run === "string" &&
          s.run.includes("exit 1") &&
          (s.run.includes("does not exist and cannot be built") || s.run.includes("::error::"))
      );
      check(
        `${name}'s 'resolve-version' job has an explicit failure path for a not-found version (no silent fallback)`,
        hasFailurePath
      );
    }
  }
}

// ---------------------------------------------------------------------
// User Story 5 — cache-miss-on-latest build fallback, distinct from the
// not-found explicit-version failure path
// ---------------------------------------------------------------------
function testUserStory5() {
  console.log("\nUser Story 5 — build-on-demand for latest, distinct from not-found failure:");

  const buildTargets = {
    "frontend-deploy.yml": "./.github/workflows/_build-frontend.yml",
    "backend-deploy.yml": "./.github/workflows/_build-backend.yml",
    "infrastructure-deploy.yml": "./.github/workflows/_build-infrastructure.yml",
  };

  for (const [name, target] of Object.entries(buildTargets)) {
    const wf = loadWorkflow(name);
    const buildJob = wf.jobs && wf.jobs["build-on-demand"];
    check(`${name} has a 'build-on-demand' job`, !!buildJob);
    if (buildJob) {
      check(
        `${name}'s 'build-on-demand' job calls ${target}`,
        buildJob.uses === target
      );
      check(
        `${name}'s 'build-on-demand' job is conditional (not unconditional)`,
        typeof buildJob.if === "string" && buildJob.if.length > 0
      );
      // Distinctness from the not-found failure path: build-on-demand must
      // be gated on cache-miss/must-build signals, not merely "job ran" —
      // an explicit not-found version fails inside resolve-version (User
      // Story 4) before build-on-demand's condition is even evaluated for
      // that reason, since resolve-version itself exits non-zero.
      check(
        `${name}'s 'build-on-demand' condition references must_build or cache_hit (the latest-not-yet-built signal), not an unconditional/failure-based trigger`,
        buildJob.if.includes("must_build") || buildJob.if.includes("cache_hit")
      );
    }
  }
}

console.log("=== Workflow structure assertion tests ===\n");
testUserStory1();
testUserStory2();
testUserStory3();
testUserStory4();
testUserStory5();

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures > 0 ? 1 : 0);
