import { render, screen } from "@testing-library/react";
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

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";
import MainMenu from "../../src/components/Menu/MainMenu.jsx";
import { CapabilitiesProvider } from "../../src/hooks/useCapabilities.js";

describe("Main Menu refresh (FR-001, FR-002, contracts/refresh-control.md)", () => {
  beforeEach(() => {
    getMe.mockReset();
    sessionStorage.clear();
  });

  it("selecting the shared nav refresh control re-fetches capabilities and updates both the menu and the nav bar without navigating away", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <CapabilitiesProvider>
          <AuthenticatedLayout>
            <MainMenu />
          </AuthenticatedLayout>
        </CapabilitiesProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /my stories/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^administration$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(1);

    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: true } });
    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    // One shared fetch updates both MainMenu's own content and NavBar's cross-link.
    expect(await screen.findByRole("button", { name: /^administration$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
    // Still on the same screen — no navigation occurred.
    expect(screen.getByRole("heading", { name: /my stories/i })).toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(2);
  });
});
