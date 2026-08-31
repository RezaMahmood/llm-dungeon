import { InteractionStatus } from "@azure/msal-browser";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const mockIsAuthenticated = vi.fn();
const mockInProgress = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useIsAuthenticated: () => mockIsAuthenticated(),
  useMsal: () => ({ instance: {}, accounts: [], inProgress: mockInProgress() }),
}));

const mockUseCapabilities = vi.fn();
vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import ProtectedRoute from "../../src/components/Auth/ProtectedRoute.jsx";

const renderRoute = () =>
  render(
    <MemoryRouter initialEntries={["/menu"]}>
      <Routes>
        <Route
          path="/menu"
          element={
            <ProtectedRoute>
              <p>protected content</p>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<p>login screen</p>} />
      </Routes>
    </MemoryRouter>,
  );

describe("ProtectedRoute inProgress x isAuthenticated matrix (contracts/reload-resilience.md Guarantee 2)", () => {
  beforeEach(() => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: false,
      loading: false,
    });
  });

  it("renders a loading state (not a redirect) while inProgress is Startup, even if isAuthenticated is currently false", () => {
    mockInProgress.mockReturnValue(InteractionStatus.Startup);
    mockIsAuthenticated.mockReturnValue(false);

    renderRoute();

    expect(screen.queryByText("login screen")).not.toBeInTheDocument();
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });

  it("renders a loading state while inProgress is Startup, even if isAuthenticated is currently true", () => {
    mockInProgress.mockReturnValue(InteractionStatus.Startup);
    mockIsAuthenticated.mockReturnValue(true);

    renderRoute();

    expect(screen.queryByText("login screen")).not.toBeInTheDocument();
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });

  it("redirects to /login once inProgress is None and isAuthenticated is false", () => {
    mockInProgress.mockReturnValue(InteractionStatus.None);
    mockIsAuthenticated.mockReturnValue(false);

    renderRoute();

    expect(screen.getByText("login screen")).toBeInTheDocument();
  });

  it("renders the protected children once inProgress is None and isAuthenticated is true", () => {
    mockInProgress.mockReturnValue(InteractionStatus.None);
    mockIsAuthenticated.mockReturnValue(true);

    renderRoute();

    expect(screen.getByText("protected content")).toBeInTheDocument();
  });
});
