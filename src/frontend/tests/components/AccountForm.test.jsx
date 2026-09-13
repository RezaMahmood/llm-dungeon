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

    expect(screen.getByLabelText(/microsoft account/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/player/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/administrator/i)).toBeInTheDocument();
  });

  it("renders the 'Add someone' panel per the canonical design", () => {
    render(<AccountForm token="tok" />);

    expect(screen.getByText("+")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /add someone/i })).toBeInTheDocument();
    expect(screen.getByText(/no password is set here/i)).toBeInTheDocument();
    expect(screen.getByText(/sees only the stories assigned to their class/i)).toBeInTheDocument();
    expect(
      screen.getByText(/creates and edits stories, adds and removes accounts/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/an account can hold both roles/i)).toBeInTheDocument();
    const submit = screen.getByRole("button", { name: /add account/i });
    expect(submit).toHaveClass("btn-primary");
    expect(submit).toHaveClass("btn-block");
  });

  it("submits the email and selected roles, then calls onAdded and clears the form", async () => {
    addAccount.mockResolvedValueOnce({ account: { email: "player@example.com", roles: ["Player"], bound: false } });
    const onAdded = vi.fn();
    render(<AccountForm token="tok" onAdded={onAdded} />);

    await userEvent.type(screen.getByLabelText(/microsoft account/i), "player@example.com");
    await userEvent.click(screen.getByLabelText(/player/i));
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(addAccount).toHaveBeenCalledWith("tok", "player@example.com", ["Player"]);
    expect(onAdded).toHaveBeenCalledWith({ email: "player@example.com", roles: ["Player"], bound: false });
    expect(screen.getByLabelText(/microsoft account/i)).toHaveValue("");
  });

  it("surfaces role_required for an empty role submission", async () => {
    addAccount.mockRejectedValueOnce({ response: { data: { error: "role_required" } } });
    render(<AccountForm token="tok" />);

    await userEvent.type(screen.getByLabelText(/microsoft account/i), "player@example.com");
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/select at least one role/i);
  });

  it("surfaces invalid_email for a malformed email", async () => {
    addAccount.mockRejectedValueOnce({ response: { data: { error: "invalid_email" } } });
    render(<AccountForm token="tok" />);

    await userEvent.type(screen.getByLabelText(/microsoft account/i), "not-an-email");
    await userEvent.click(screen.getByLabelText(/player/i));
    await userEvent.click(screen.getByRole("button", { name: /add account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/valid email/i);
  });
});
