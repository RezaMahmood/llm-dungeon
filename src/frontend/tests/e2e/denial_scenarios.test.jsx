import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();
const mockAccounts = [{ homeAccountId: "home-1", username: "player@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: { logoutRedirect: vi.fn(), acquireTokenSilent: vi.fn() }, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

// hasPlayer is false in both scenarios below, so HomePage's data fetch short-circuits
// before ever calling these — mocked only so the module import resolves.
vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: vi.fn(),
  listSavedGames: vi.fn(),
}));

import HomePage from "../../src/pages/HomePage.jsx";

describe("Denial scenarios", () => {
  it("valid token, not on allow-list: shows denied message, no home content", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: false,
      loading: false,
      error: null,
      denied: true,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/access not granted/i);
    expect(screen.queryByText(/ready to play/i)).not.toBeInTheDocument();
  });

  it("valid token, on allow-list, no capabilities: shows provisioning message", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: false,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/access pending/i)).toBeInTheDocument();
  });
});
