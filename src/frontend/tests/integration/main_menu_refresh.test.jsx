import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "ada@example.test", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

const getMe = vi.fn();
vi.mock("../../src/services/authService.js", () => ({
  getMe: (...args) => getMe(...args),
}));

const listAdventures = vi.fn().mockResolvedValue({ adventures: [] });
const listSavedGames = vi.fn().mockResolvedValue({ sessions: [] });
vi.mock("../../src/services/gameService.js", () => ({
  listAdventures: (...args) => listAdventures(...args),
  listSavedGames: (...args) => listSavedGames(...args),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";
import HomePage from "../../src/pages/HomePage.jsx";
import { CapabilitiesProvider } from "../../src/hooks/useCapabilities.js";

describe("Home refresh (FR-001, FR-002, contracts/refresh-control.md)", () => {
  beforeEach(() => {
    getMe.mockReset();
    sessionStorage.clear();
  });

  it("selecting the shared nav refresh control re-fetches capabilities and updates both Home's nav and its own data without navigating away", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <CapabilitiesProvider>
          <AuthenticatedLayout>
            <HomePage />
          </AuthenticatedLayout>
        </CapabilitiesProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /ready to play/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "New story" })).not.toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(1);
    // Home's own data fetch is a separate effect from the capability check above, so it
    // may still be in flight the instant the heading first appears.
    await waitFor(() => expect(listAdventures).toHaveBeenCalledTimes(1));

    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: true } });
    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    // One shared refresh updates both NavBar's admin links and Home's own game data.
    expect(await screen.findByRole("link", { name: "Admin" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New story" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
    // Still on the same screen — no navigation occurred.
    expect(screen.getByRole("heading", { name: /ready to play/i })).toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(listAdventures).toHaveBeenCalledTimes(2));
  });
});
