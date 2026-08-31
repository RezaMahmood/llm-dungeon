import { InteractionStatus } from "@azure/msal-browser";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Simulates a hard reload: MSAL starts with `inProgress: Startup` while it
// reads its cached session from localStorage, then settles to `None` with a
// valid cached account — mirroring contracts/reload-resilience.md Guarantee 2.
let inProgress = InteractionStatus.Startup;
let isAuthenticated = false;

vi.mock("@azure/msal-react", () => ({
  useIsAuthenticated: () => isAuthenticated,
  useMsal: () => ({
    instance: { logoutRedirect: vi.fn() },
    accounts: [{ homeAccountId: "home-1", username: "admin@example.com", name: "Admin A." }],
    inProgress,
  }),
}));

const mockUseCapabilities = vi.fn();
vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import ProtectedRoute from "../../src/components/Auth/ProtectedRoute.jsx";

describe("Reload resilience: a hard reload on a nested route (FR-007, FR-009)", () => {
  beforeEach(() => {
    inProgress = InteractionStatus.Startup;
    isAuthenticated = false;
    mockUseCapabilities.mockReturnValue({ hasPlayer: false, hasAdministrator: true, loading: false });
  });

  it("does not redirect to /login before MSAL initialization completes, then renders the originally-requested nested screen", () => {
    const { rerender } = render(
      <MemoryRouter initialEntries={["/admin/stories/new"]}>
        <Routes>
          <Route
            path="/admin/stories/new"
            element={
              <ProtectedRoute capability="Administrator">
                <p>story wizard</p>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<p>login screen</p>} />
        </Routes>
      </MemoryRouter>,
    );

    // Mid-initialization: no redirect, no premature render of protected content.
    expect(screen.queryByText("login screen")).not.toBeInTheDocument();
    expect(screen.queryByText("story wizard")).not.toBeInTheDocument();

    // MSAL finishes reading the cached session: it was valid all along.
    inProgress = InteractionStatus.None;
    isAuthenticated = true;

    rerender(
      <MemoryRouter initialEntries={["/admin/stories/new"]}>
        <Routes>
          <Route
            path="/admin/stories/new"
            element={
              <ProtectedRoute capability="Administrator">
                <p>story wizard</p>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<p>login screen</p>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("story wizard")).toBeInTheDocument();
    expect(screen.queryByText("login screen")).not.toBeInTheDocument();
  });
});
