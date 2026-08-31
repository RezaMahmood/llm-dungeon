import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useRefreshable } from "../../src/hooks/useRefreshable.js";

describe("useRefreshable", () => {
  it("fires refresh() once automatically on mount", async () => {
    const fetchFn = vi.fn().mockResolvedValue("payload");
    renderHook(() => useRefreshable(fetchFn));

    await waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(1));
  });

  it("replaces data and clears error on a successful fetch", async () => {
    const fetchFn = vi.fn().mockResolvedValue("payload");
    const { result } = renderHook(() => useRefreshable(fetchFn));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBe("payload");
    expect(result.current.error).toBeNull();
  });

  it("leaves prior data unchanged and sets error without throwing on a rejected fetch (FR-005)", async () => {
    const fetchFn = vi.fn().mockResolvedValueOnce("first").mockRejectedValueOnce(new Error("boom"));
    const { result } = renderHook(() => useRefreshable(fetchFn));

    await waitFor(() => expect(result.current.data).toBe("first"));

    await result.current.refresh();

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBe("first");
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it("is a no-op if refresh() is called again while a fetch is already pending (FR-004)", async () => {
    let resolveFetch;
    const fetchFn = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFetch = resolve;
          }),
      )
      .mockResolvedValue("second-call-payload");

    const { result } = renderHook(() => useRefreshable(fetchFn));
    await waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(1));

    // A second call while the first is still in flight must not invoke fetchFn again.
    result.current.refresh();
    expect(fetchFn).toHaveBeenCalledTimes(1);

    resolveFetch("first-call-payload");
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBe("first-call-payload");
  });
});
