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

  it("drops the admin-only nav item after a refresh returns reduced capabilities", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: true } });
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <AuthenticatedLayout>
          <MainMenu />
        </AuthenticatedLayout>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("link", { name: "Admin" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    await screen.findByText(/my stories/i);
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
    expect(getMe).toHaveBeenCalledTimes(2);
  });
});
