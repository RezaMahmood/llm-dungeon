import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const addAccount = vi.fn();

vi.mock("../../src/services/accountService.js", () => ({
  addAccount: (...args) => addAccount(...args),
}));

import AccountForm from "../../src/components/Admin/AccountForm.jsx";

describe("AccountForm", () => {
  beforeEach(() => {
    addAccount.mockReset();
  });

  it("renders the email field and role checkboxes", () => {
    render(<AccountForm token="tok" />);

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/player/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/administrator/i)).toBeInTheDocument();
  });

  it("submits the email and selected roles, then calls onAdded and clears the form", async () => {
    addAccount.mockResolvedValueOnce({ account: { email: "player@example.com", roles: ["Player"], bound: false } });
    const onAdded = vi.fn();
    render(<AccountForm token="tok" onAdded={onAdded} />);

    await userEvent.type(screen.getByLabelText(/email/i), "player@example.com");
    await userEvent.click(screen.getByLabelText(/player/i));
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(addAccount).toHaveBeenCalledWith("tok", "player@example.com", ["Player"]);
    expect(onAdded).toHaveBeenCalledWith({ email: "player@example.com", roles: ["Player"], bound: false });
    expect(screen.getByLabelText(/email/i)).toHaveValue("");
  });

  it("surfaces role_required for an empty role submission", async () => {
    addAccount.mockRejectedValueOnce({ response: { data: { error: "role_required" } } });
    render(<AccountForm token="tok" />);

    await userEvent.type(screen.getByLabelText(/email/i), "player@example.com");
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/select at least one role/i);
  });

  it("surfaces invalid_email for a malformed email", async () => {
    addAccount.mockRejectedValueOnce({ response: { data: { error: "invalid_email" } } });
    render(<AccountForm token="tok" />);

    await userEvent.type(screen.getByLabelText(/email/i), "not-an-email");
    await userEvent.click(screen.getByLabelText(/player/i));
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/valid email/i);
  });
});
