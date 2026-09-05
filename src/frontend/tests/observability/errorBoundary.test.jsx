import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const trackException = vi.fn();

vi.mock("../../src/observability/appInsights.js", () => ({
  appInsights: { trackException },
}));

const { ErrorBoundary } = await import("../../src/observability/ErrorBoundary.jsx");

function Thrower() {
  throw new Error("render blew up");
}

describe("observability/ErrorBoundary", () => {
  it("reports a caught render error to Application Insights and shows the fallback UI", () => {
    // eslint-disable-next-line no-console -- React logs the caught error; expected noise for this test
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Thrower />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
    expect(trackException).toHaveBeenCalledTimes(1);
    const call = trackException.mock.calls[0][0];
    expect(call.exception).toBeInstanceOf(Error);
    expect(call.exception.message).toBe("render blew up");

    consoleError.mockRestore();
  });
});
