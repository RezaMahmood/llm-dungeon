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

describe("Main Menu refresh (FR-001, FR-002, contracts/refresh-control.md)", () => {
  beforeEach(() => {
    getMe.mockReset();
    sessionStorage.clear();
  });

  it("selecting the shared nav refresh control re-fetches capabilities and updates the menu without navigating away", async () => {
    // NavBar mounts its own independent useCapabilities() call (022's own concern,
    // unrelated to this screen's refresh), so the initial mount fires more than one
    // /api/auth/me call. Default every call to Player-only, then arm exactly the next
    // call after we click the shared refresh control — that's the one this test cares about.
    getMe.mockResolvedValue({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <AuthenticatedLayout>
          <MainMenu />
        </AuthenticatedLayout>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /my stories/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^administration$/i })).not.toBeInTheDocument();

    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: true } });
    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByRole("button", { name: /^administration$/i })).toBeInTheDocument();
    // Still on the same screen — no navigation occurred.
    expect(screen.getByRole("heading", { name: /my stories/i })).toBeInTheDocument();
  });
});
