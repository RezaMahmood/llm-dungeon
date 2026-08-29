import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const addAccount = vi.fn();
const listAccounts = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({
    instance: { acquireTokenSilent },
    accounts: [{ homeAccountId: "home-1", username: "admin@example.com" }],
  }),
}));

vi.mock("../../src/services/accountService.js", () => ({
  addAccount: (...args) => addAccount(...args),
  listAccounts: (...args) => listAccounts(...args),
}));

import AdminAccountsPage from "../../src/pages/AdminAccountsPage.jsx";

describe("Admin accounts: add -> list -> re-add merges", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    addAccount.mockReset();
    listAccounts.mockReset();
  });

  it("lists provisioned accounts on load, then adding one refreshes the list", async () => {
    listAccounts
      .mockResolvedValueOnce({ accounts: [{ email: "admin@example.com", roles: ["Administrator"], bound: true }] })
      .mockResolvedValueOnce({
        accounts: [
          { email: "admin@example.com", roles: ["Administrator"], bound: true },
          { email: "player@example.com", roles: ["Player"], bound: false },
        ],
      });
    addAccount.mockResolvedValueOnce({ account: { email: "player@example.com", roles: ["Player"], bound: false } });

    render(<AdminAccountsPage />);

    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/email/i), "player@example.com");
    await userEvent.click(screen.getByLabelText(/player/i));
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(await screen.findByText("player@example.com")).toBeInTheDocument();
    expect(listAccounts).toHaveBeenCalledTimes(2);
  });

  it("re-adding an already-provisioned email with an extra role merges into one entry", async () => {
    listAccounts
      .mockResolvedValueOnce({ accounts: [{ email: "player@example.com", roles: ["Player"], bound: true }] })
      .mockResolvedValueOnce({
        accounts: [{ email: "player@example.com", roles: ["Administrator", "Player"], bound: true }],
      });
    addAccount.mockResolvedValueOnce({
      account: { email: "player@example.com", roles: ["Administrator", "Player"], bound: true },
    });

    render(<AdminAccountsPage />);

    expect(await screen.findByText("player@example.com")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(2); // header + one entry

    await userEvent.type(screen.getByLabelText(/email/i), "player@example.com");
    await userEvent.click(screen.getByLabelText(/administrator/i));
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    await screen.findByText("Administrator");
    expect(screen.getAllByRole("row")).toHaveLength(2); // still one merged entry, not two
  });
});
