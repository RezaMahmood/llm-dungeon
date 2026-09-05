import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

async function waitFor(predicate, { timeout = 5000, interval = 20 } = {}) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
  throw new Error("waitFor: condition not met within timeout");
}

describe("observability: frontend-only dependency failure (FR-005a)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=00000000-0000-0000-0000-000000000000");
  });

  it("emits a Dependency-failure telemetry event for an outbound call that never reaches the backend", async () => {
    const { appInsights, initializeAppInsights } = await import("../../src/observability/appInsights.js");
    initializeAppInsights();

    const captured = [];
    appInsights.addTelemetryInitializer((item) => {
      captured.push(item);
      return false; // don't actually send telemetry to a real endpoint in this test
    });

    // No server listens on this port — a real network failure, not a mocked one,
    // so this is the exact "backend never saw it" scenario FR-005a exists for.
    await axios.get("http://127.0.0.1:1/never-reached", { timeout: 2000 }).catch(() => {});
    await waitFor(() => captured.some((item) => item.baseType === "RemoteDependencyData"));

    const dependencyEvents = captured.filter((item) => item.baseType === "RemoteDependencyData");
    expect(dependencyEvents).toHaveLength(1);
    expect(dependencyEvents[0].baseData.success).toBe(false);
    expect(dependencyEvents[0].baseData.responseCode).toBe(0);
  }, 10000);
});
