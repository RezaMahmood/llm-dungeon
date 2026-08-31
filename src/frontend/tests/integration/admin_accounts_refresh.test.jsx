import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "tok" });
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Admin A." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

const mockUseCapabilities = vi.fn();
vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

const listAccounts = vi.fn();
vi.mock("../../src/services/accountService.js", () => ({
  addAccount: vi.fn(),
  listAccounts: (...args) => listAccounts(...args),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";
import AdminAccountsPage from "../../src/pages/AdminAccountsPage.jsx";

describe("Admin Accounts refresh (FR-001, FR-002, FR-005)", () => {
  beforeEach(() => {
    listAccounts.mockReset();
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: true,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });
  });

  const renderPage = () =>
    render(
      <MemoryRouter initialEntries={["/admin/accounts"]}>
        <AuthenticatedLayout>
          <AdminAccountsPage />
        </AuthenticatedLayout>
      </MemoryRouter>,
    );

  it("selecting the refresh control re-fetches the account list", async () => {
    listAccounts
      .mockResolvedValueOnce({ accounts: [{ email: "one@example.com", roles: ["Player"] }] })
      .mockResolvedValueOnce({
        accounts: [
          { email: "one@example.com", roles: ["Player"] },
          { email: "two@example.com", roles: ["Player"] },
        ],
      });

    renderPage();

    expect(await screen.findByText("one@example.com")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByText("two@example.com")).toBeInTheDocument();
    expect(listAccounts).toHaveBeenCalledTimes(2);
  });

  it("shows an inline error and leaves the previously-loaded list visible on a rejected refresh (FR-005)", async () => {
    listAccounts
      .mockResolvedValueOnce({ accounts: [{ email: "one@example.com", roles: ["Player"] }] })
      .mockRejectedValueOnce(new Error("network down"));

    renderPage();

    expect(await screen.findByText("one@example.com")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("one@example.com")).toBeInTheDocument();
  });
});
