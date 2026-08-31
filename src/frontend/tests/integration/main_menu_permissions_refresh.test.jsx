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

describe("Main Menu reflects permissions revoked between load and refresh (FR-011)", () => {
  beforeEach(() => {
    getMe.mockReset();
    sessionStorage.clear();
  });

  it("drops the admin-only menu item after a refresh returns reduced capabilities", async () => {
    // NavBar mounts its own independent useCapabilities() call (022's own concern,
    // separate from MainMenu's), so the initial mount fires more than one /api/auth/me
    // call. Default every call to dual-capability, then arm exactly the next call
    // after clicking refresh — that's the one MainMenu's own refetch consumes.
    getMe.mockResolvedValue({ capabilities: { hasPlayer: true, hasAdministrator: true } });

    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <AuthenticatedLayout>
          <MainMenu />
        </AuthenticatedLayout>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("button", { name: /^administration$/i })).toBeInTheDocument();

    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });
    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    await screen.findByRole("heading", { name: /my stories/i });
    expect(screen.queryByRole("button", { name: /^administration$/i })).not.toBeInTheDocument();
  });
});
