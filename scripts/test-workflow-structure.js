#!/usr/bin/env node
// Workflow-structure assertion tests for specs/023-cicd-pipeline-optimization.
//
// Covers User Stories 1, 2, and 5 (tasks.md T006, T010, T026) — static
// YAML-shape checks that `actionlint` alone does not perform (it only
// checks syntax/schema, not job/step content). Run with:
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
  return yaml.load(raw);
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

// ---------------------------------------------------------------------
// User Story 1 — build-once/deploy-that-artifact
// ---------------------------------------------------------------------
function testUserStory1() {
  console.log("User Story 1 — deploy consumes build's artifact, no rebuild:");

  const backend = loadWorkflow("backend-deploy.yml");
  const backendDeploy = backend.jobs && backend.jobs.deploy;
  check("backend-deploy.yml has a 'deploy' job", !!backendDeploy);
  if (backendDeploy) {
    const steps = stepsOf(backendDeploy);
    check(
      "backend 'deploy' job has no pip install step",
      !stepRunContains(steps, "pip install")
    );
    const functionsAction = findStepUsing(steps, "Azure/functions-action");
    check("backend 'deploy' job calls Azure/functions-action", !!functionsAction);
    check(
      // remote-build MUST be true, not false: this Function App's Flex
      // Consumption plan does not support a pre-built/vendored-dependency
      // Python package — confirmed empirically 2026-09-01 (PR #149) when
      // remote-build: false deployed "successfully" but loaded zero
      // functions. Deploy still doesn't reinstall deps or re-run tests
      // itself (checked above/below); the remote Oryx build is a real,
      // unavoidable platform constraint for this plan type.
      "backend 'deploy' job's functions-action sets remote-build: true (Flex Consumption requires it)",
      !!functionsAction && functionsAction.with && functionsAction.with["remote-build"] === true
    );
    check(
      "backend 'deploy' job downloads a build artifact",
      !!findStepUsing(steps, "actions/download-artifact")
    );
  }

  const backendBuild = backend.jobs && backend.jobs.build;
  check("backend-deploy.yml has a 'build' job", !!backendBuild);
  let backendUploadName;
  if (backendBuild) {
    const uploadStep = findStepUsing(stepsOf(backendBuild), "actions/upload-artifact");
    check("backend 'build' job uploads an artifact", !!uploadStep);
    backendUploadName = uploadStep && uploadStep.with && uploadStep.with.name;
  }
  if (backendDeploy) {
    const downloadStep = findStepUsing(stepsOf(backendDeploy), "actions/download-artifact");
    const backendDownloadName = downloadStep && downloadStep.with && downloadStep.with.name;
    check(
      "backend build→deploy artifact names match",
      !!backendUploadName && backendUploadName === backendDownloadName
    );
  }

  const frontend = loadWorkflow("frontend-deploy.yml");
  const frontendDeploy = frontend.jobs && frontend.jobs.deploy;
  check("frontend-deploy.yml has a 'deploy' job", !!frontendDeploy);
  if (frontendDeploy) {
    const steps = stepsOf(frontendDeploy);
    check(
      "frontend 'deploy' job has no npm install/build step",
      !stepRunContains(steps, "npm install") && !stepRunContains(steps, "npm run build")
    );
    const swaAction = findStepUsing(steps, "Azure/static-web-apps-deploy");
    check("frontend 'deploy' job calls Azure/static-web-apps-deploy", !!swaAction);
    check(
      "frontend 'deploy' job's static-web-apps-deploy sets skip_app_build: true",
      !!swaAction && swaAction.with && swaAction.with.skip_app_build === true
    );
    check(
      "frontend 'deploy' job downloads a build artifact",
      !!findStepUsing(steps, "actions/download-artifact")
    );
  }

  const frontendBuild = frontend.jobs && frontend.jobs.build;
  check("frontend-deploy.yml has a 'build' job", !!frontendBuild);
  let frontendUploadName;
  if (frontendBuild) {
    const uploadStep = findStepUsing(stepsOf(frontendBuild), "actions/upload-artifact");
    check("frontend 'build' job uploads an artifact", !!uploadStep);
    frontendUploadName = uploadStep && uploadStep.with && uploadStep.with.name;
  }
  if (frontendDeploy) {
    const downloadStep = findStepUsing(stepsOf(frontendDeploy), "actions/download-artifact");
    const frontendDownloadName = downloadStep && downloadStep.with && downloadStep.with.name;
    check(
      "frontend build→deploy artifact names match",
      !!frontendUploadName && frontendUploadName === frontendDownloadName
    );
  }
}

// ---------------------------------------------------------------------
// User Story 2 — concurrency-based stale-deploy cancellation
// ---------------------------------------------------------------------
function testUserStory2() {
  console.log("User Story 2 — concurrency cancellation:");

  const backend = loadWorkflow("backend-deploy.yml");
  check(
    "backend-deploy.yml has concurrency.group === 'deploy-backend'",
    !!backend.concurrency && backend.concurrency.group === "deploy-backend"
  );
  check(
    "backend-deploy.yml has concurrency.cancel-in-progress === true",
    !!backend.concurrency && backend.concurrency["cancel-in-progress"] === true
  );

  const frontend = loadWorkflow("frontend-deploy.yml");
  check(
    "frontend-deploy.yml has concurrency.group === 'deploy-frontend'",
    !!frontend.concurrency && frontend.concurrency.group === "deploy-frontend"
  );
  check(
    "frontend-deploy.yml has concurrency.cancel-in-progress === true",
    !!frontend.concurrency && frontend.concurrency["cancel-in-progress"] === true
  );
}

// ---------------------------------------------------------------------
// User Story 5 — Terraform apply-the-reviewed-plan
// ---------------------------------------------------------------------
function testUserStory5() {
  console.log("User Story 5 — terraform apply uses the saved plan:");

  const tf = loadWorkflow("terraform-apply.yml");
  const validateJob = tf.jobs && tf.jobs.validate;
  check("terraform-apply.yml has a 'validate' job", !!validateJob);
  if (validateJob) {
    const steps = stepsOf(validateJob);
    check(
      "'validate' job's terraform plan step writes -out=tfplan",
      stepRunContains(steps, "-out=tfplan")
    );
    check(
      "'validate' job uploads the tfplan artifact",
      !!findStepUsing(steps, "actions/upload-artifact")
    );
  }

  const applyJob = tf.jobs && tf.jobs.apply;
  check("terraform-apply.yml has an 'apply' job", !!applyJob);
  if (applyJob) {
    const steps = stepsOf(applyJob);
    check(
      "'apply' job downloads the tfplan artifact",
      !!findStepUsing(steps, "actions/download-artifact")
    );
    check(
      "'apply' job's terraform apply command references the tfplan file",
      stepRunContains(steps, "terraform apply") && stepRunContains(steps, "tfplan")
    );
    check(
      "'apply' job's terraform apply command has no -auto-approve flag",
      !stepRunContains(steps, "-auto-approve")
    );
    check(
      "'apply' job's terraform apply command has no -var-file flag",
      !stepRunContains(steps, "-var-file")
    );
  }
}

console.log("=== Workflow structure assertion tests ===\n");
testUserStory1();
console.log("");
testUserStory2();
console.log("");
testUserStory5();

console.log(`\n${passes} passed, ${failures} failed`);
process.exit(failures > 0 ? 1 : 0);
