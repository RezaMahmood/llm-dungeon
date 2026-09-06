import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import LogoutSavePrompt from "../../src/components/Layout/LogoutSavePrompt.jsx";

describe("LogoutSavePrompt (009-save-and-continue, FR-004, FR-005)", () => {
  it("states that progress is already safe", () => {
    render(<LogoutSavePrompt saving={false} failureMessage={null} onSave={() => {}} onDontSave={() => {}} onCancel={() => {}} />);

    expect(screen.getByText(/progress is already safe/i)).toBeInTheDocument();
  });

  it("calls onSave when Save and sign out is clicked", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<LogoutSavePrompt saving={false} failureMessage={null} onSave={onSave} onDontSave={() => {}} onCancel={() => {}} />);

    await user.click(screen.getByRole("button", { name: /save and sign out/i }));

    expect(onSave).toHaveBeenCalledOnce();
  });

  it("calls onDontSave when Sign out without saving is clicked", async () => {
    const onDontSave = vi.fn();
    const user = userEvent.setup();
    render(<LogoutSavePrompt saving={false} failureMessage={null} onSave={() => {}} onDontSave={onDontSave} onCancel={() => {}} />);

    await user.click(screen.getByRole("button", { name: /sign out without saving/i }));

    expect(onDontSave).toHaveBeenCalledOnce();
  });

  it("calls onCancel and does neither save nor sign out when Cancel is clicked", async () => {
    const onSave = vi.fn();
    const onDontSave = vi.fn();
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<LogoutSavePrompt saving={false} failureMessage={null} onSave={onSave} onDontSave={onDontSave} onCancel={onCancel} />);

    await user.click(screen.getByRole("button", { name: /^cancel$/i }));

    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSave).not.toHaveBeenCalled();
    expect(onDontSave).not.toHaveBeenCalled();
  });

  it("renders the failure notice inline without requiring acknowledgement (FR-006a)", () => {
    render(
      <LogoutSavePrompt
        saving={false}
        failureMessage="We couldn't record that checkpoint, but your progress is safe."
        onSave={() => {}}
        onDontSave={() => {}}
        onCancel={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/couldn't record that checkpoint/i);
    // No acknowledgement control beyond the prompt's own actions.
    expect(screen.getByRole("button", { name: /save and sign out/i })).toBeInTheDocument();
  });

  it("is keyboard-operable with a real dialog role and labelled title", () => {
    render(<LogoutSavePrompt saving={false} failureMessage={null} onSave={() => {}} onDontSave={() => {}} onCancel={() => {}} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-labelledby", "logout-save-prompt-title");
    for (const name of [/save and sign out/i, /sign out without saving/i, /^cancel$/i]) {
      expect(screen.getByRole("button", { name })).toBeVisible();
    }
  });
});
