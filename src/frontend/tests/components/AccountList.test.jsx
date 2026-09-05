import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const removeAccount = vi.fn();

vi.mock("../../src/services/accountService.js", () => ({
  removeAccount: (...args) => removeAccount(...args),
}));

import AccountList from "../../src/components/Admin/AccountList.jsx";

describe("AccountList", () => {
  beforeEach(() => {
    removeAccount.mockReset();
  });

  it("lists every account with its email and roles", () => {
    render(
      <AccountList
        accounts={[
          { email: "admin@example.com", roles: ["Administrator"], bound: true },
          { email: "player@example.com", roles: ["Player"], bound: false },
        ]}
      />,
    );

    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("player@example.com")).toBeInTheDocument();
    expect(screen.getByText("Administrator")).toBeInTheDocument();
    expect(screen.getByText("Player")).toBeInTheDocument();
  });

  it("shows both roles for a merged dual-role account without duplicating rows", () => {
    render(
      <AccountList
        accounts={[{ email: "dual@example.com", roles: ["Player", "Administrator"], bound: true }]}
      />,
    );

    const rows = screen.getAllByRole("row");
    // header row + exactly one data row
    expect(rows).toHaveLength(2);
    expect(screen.getByText("Player")).toBeInTheDocument();
    expect(screen.getByText("Administrator")).toBeInTheDocument();
  });

  it("shows bound status as Signed in / Pending first sign-in", () => {
    render(
      <AccountList
        accounts={[
          { email: "admin@example.com", roles: ["Administrator"], bound: true },
          { email: "player@example.com", roles: ["Player"], bound: false },
        ]}
      />,
    );

    expect(screen.getByText("Signed in")).toBeInTheDocument();
    expect(screen.getByText("Pending first sign-in")).toBeInTheDocument();
  });

  it("renders an empty table when there are no accounts", () => {
    render(<AccountList accounts={[]} />);

    expect(screen.getAllByRole("row")).toHaveLength(1);
  });

  // --- Delete action (T065) ---

  it("opens a confirmation dialog before removing, and does not call removeAccount yet", async () => {
    render(
      <AccountList
        accounts={[{ email: "player@example.com", roles: ["Player"], bound: true }]}
        token="tok"
        currentUserEmail="admin@example.com"
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));

    expect(screen.getByRole("dialog")).toHaveTextContent(/remove player@example\.com\?/i);
    expect(removeAccount).not.toHaveBeenCalled();
  });

  it("calls removeAccount and notifies onRemoved when the confirmation is confirmed", async () => {
    removeAccount.mockResolvedValueOnce({ status: "success" });
    const onRemoved = vi.fn();
    render(
      <AccountList
        accounts={[{ email: "player@example.com", roles: ["Player"], bound: true }]}
        token="tok"
        currentUserEmail="admin@example.com"
        onRemoved={onRemoved}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));
    await userEvent.click(screen.getByRole("button", { name: /remove account/i }));

    expect(removeAccount).toHaveBeenCalledWith("tok", "player@example.com");
    expect(onRemoved).toHaveBeenCalledWith("player@example.com");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not call removeAccount when cancelling with Keep it", async () => {
    render(
      <AccountList
        accounts={[{ email: "player@example.com", roles: ["Player"], bound: true }]}
        token="tok"
        currentUserEmail="admin@example.com"
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));
    await userEvent.click(screen.getByRole("button", { name: /keep it/i }));

    expect(removeAccount).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("hides the remove action for the signed-in administrator's own row", () => {
    render(
      <AccountList
        accounts={[
          { email: "admin@example.com", roles: ["Administrator"], bound: true },
          { email: "player@example.com", roles: ["Player"], bound: true },
        ]}
        token="tok"
        currentUserEmail="admin@example.com"
      />,
    );

    expect(screen.getAllByRole("button", { name: /^remove$/i })).toHaveLength(1);
  });

  it("hides the remove action for the seed administrator's row", () => {
    render(
      <AccountList
        accounts={[
          { email: "seed-admin@example.com", roles: ["Administrator"], bound: true, isSeedAdmin: true },
          { email: "player@example.com", roles: ["Player"], bound: true },
        ]}
        token="tok"
        currentUserEmail="someone-else@example.com"
      />,
    );

    expect(screen.getAllByRole("button", { name: /^remove$/i })).toHaveLength(1);
  });
});
