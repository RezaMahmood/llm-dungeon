import http from "node:http";

import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * FR-005 / contract §4: an outbound call that *does* reach the backend must carry a
 * `traceparent` header so the backend request span it triggers is parented under the
 * same trace — the frontend half of "one user action, two systems, one trace" (the
 * backend half is `src/backend/tests/integration/test_observability_correlation.py`).
 */
describe("observability: frontend->backend trace correlation (FR-005)", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=00000000-0000-0000-0000-000000000000");
  });

  it("attaches a W3C traceparent header to an outbound call the AjaxPlugin observes", async () => {
    let receivedTraceparent;
    const server = http.createServer((req, res) => {
      receivedTraceparent = req.headers["traceparent"];
      res.writeHead(200, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
      });
      res.end("ok");
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const { port } = server.address();

    const { initializeAppInsights } = await import("../../src/observability/appInsights.js");
    initializeAppInsights();

    await axios.get(`http://127.0.0.1:${port}/ping`);
    await new Promise((resolve) => setTimeout(resolve, 200));

    await new Promise((resolve) => server.close(resolve));

    expect(receivedTraceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$/);
  }, 10000);
});
