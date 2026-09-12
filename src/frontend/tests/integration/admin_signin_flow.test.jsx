import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];
const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: { logoutRedirect: vi.fn(), acquireTokenSilent }, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: vi.fn().mockResolvedValue({ adventures: [] }),
  listSavedGames: vi.fn().mockResolvedValue({ sessions: [] }),
}));

import HomePage from "../../src/pages/HomePage.jsx";

describe("Admin sign-in flow", () => {
  it("reaches the full Home page for a dual-capability user, not a denial/pending state", async () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: true,
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

    // A dual-capability account gets the same Home content as a player-only one
    // (FR-011: role only changes the nav, not this page) — reaching it at all is what
    // matters here, not being stuck behind "Access Pending" or a denial screen.
    expect(await screen.findByText(/ready to play/i)).toBeInTheDocument();
    expect(screen.getByText(/in progress/i)).toBeInTheDocument();
    expect(screen.queryByText(/access pending/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert", { name: /access not granted/i })).not.toBeInTheDocument();
  });
});
