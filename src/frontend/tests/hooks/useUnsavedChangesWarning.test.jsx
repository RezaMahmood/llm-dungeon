import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useUnsavedChangesWarning } from "../../src/hooks/useUnsavedChangesWarning.js";

describe("useUnsavedChangesWarning (FR-010, data-model.md Unsaved-Changes Flag)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches a beforeunload listener only while isDirty is true", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { rerender } = renderHook(({ isDirty }) => useUnsavedChangesWarning(isDirty), {
      initialProps: { isDirty: false },
    });

    expect(addSpy).not.toHaveBeenCalledWith("beforeunload", expect.any(Function));

    rerender({ isDirty: true });
    expect(addSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));

    rerender({ isDirty: false });
    expect(removeSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
  });

  it("removes the listener on unmount while still dirty", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useUnsavedChangesWarning(true));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
  });
});
