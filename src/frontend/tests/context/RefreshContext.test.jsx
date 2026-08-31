import { render, renderHook, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  RefreshProvider,
  usePublishRefresh,
  useRefreshContext,
} from "../../src/context/RefreshContext.jsx";

describe("RefreshContext", () => {
  it("returns null from useRefreshContext when nothing has published", () => {
    const { result } = renderHook(() => useRefreshContext(), {
      wrapper: RefreshProvider,
    });

    expect(result.current).toBeNull();
  });

  it("sets the context value while the publishing component is mounted, and clears it on unmount", () => {
    const refresh = vi.fn();

    function Publisher() {
      usePublishRefresh({ refresh, loading: false });
      return null;
    }

    function Reader() {
      const published = useRefreshContext();
      return <div data-testid="reader">{published ? "published" : "empty"}</div>;
    }

    function App({ showPublisher }) {
      return (
        <RefreshProvider>
          {showPublisher && <Publisher />}
          <Reader />
        </RefreshProvider>
      );
    }

    const { rerender } = render(<App showPublisher />);
    expect(screen.getByTestId("reader")).toHaveTextContent("published");

    rerender(<App showPublisher={false} />);
    expect(screen.getByTestId("reader")).toHaveTextContent("empty");
  });
});
