import { beforeEach, describe, expect, it, vi } from "vitest";

const loadAppInsights = vi.fn();
const trackException = vi.fn();

vi.mock("@microsoft/applicationinsights-web", () => ({
  ApplicationInsights: vi.fn().mockImplementation(function ApplicationInsightsMock(options) {
    this.config = options.config;
    this.loadAppInsights = loadAppInsights;
    this.trackException = trackException;
  }),
  DistributedTracingModes: { W3C: 1 },
}));

vi.mock("@microsoft/applicationinsights-react-js", () => ({
  ReactPlugin: vi.fn().mockImplementation(function ReactPluginMock() {}),
}));

describe("observability/appInsights", () => {
  beforeEach(() => {
    vi.resetModules();
    loadAppInsights.mockClear();
    trackException.mockClear();
    vi.stubEnv("VITE_APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test-key");
  });

  it("initializes the SDK exactly once at startup with W3C distributed tracing and CORS correlation", async () => {
    const { appInsights, initializeAppInsights } = await import("../../src/observability/appInsights.js");

    expect(appInsights.config.distributedTracingMode).toBe(1);
    expect(appInsights.config.enableCorsCorrelation).toBe(true);

    initializeAppInsights();
    initializeAppInsights();
    initializeAppInsights();

    expect(loadAppInsights).toHaveBeenCalledTimes(1);
  });

  it("does not load the SDK when no connection string is configured", async () => {
    vi.stubEnv("VITE_APPLICATIONINSIGHTS_CONNECTION_STRING", "");
    const { initializeAppInsights } = await import("../../src/observability/appInsights.js");

    initializeAppInsights();

    expect(loadAppInsights).not.toHaveBeenCalled();
  });

  it("reports an unhandled window error as an Exception (FR-004, contract §3)", async () => {
    const { initializeAppInsights } = await import("../../src/observability/appInsights.js");
    initializeAppInsights();

    const error = new Error("outside react tree");
    window.dispatchEvent(new ErrorEvent("error", { error, message: error.message }));

    expect(trackException).toHaveBeenCalled();
    expect(trackException.mock.calls.at(-1)[0].exception).toBe(error);
  });

  it("reports an unhandled promise rejection as an Exception (FR-004, contract §3)", async () => {
    const { initializeAppInsights } = await import("../../src/observability/appInsights.js");
    initializeAppInsights();

    const error = new Error("rejected outside react tree");
    const event = new Event("unhandledrejection");
    event.reason = error;
    window.dispatchEvent(event);

    expect(trackException).toHaveBeenCalled();
    expect(trackException.mock.calls.at(-1)[0].exception).toBe(error);
  });
});
