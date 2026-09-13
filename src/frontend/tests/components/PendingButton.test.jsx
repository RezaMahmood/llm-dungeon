import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import PendingButton from "../../src/components/Common/PendingButton.jsx";

// The shared pending-action primitive (issue #347). These cover the contract the
// destructive actions rely on; the delete flows themselves are covered by
// StoryDeleteAction / SessionDeleteAction / admin_sessions_delete.
describe("PendingButton (issue #347)", () => {
  it("is an ordinary button when nothing is pending", async () => {
    const onClick = vi.fn();
    render(<PendingButton onClick={onClick}>Delete</PendingButton>);

    const button = screen.getByRole("button", { name: "Delete" });
    expect(button).toBeEnabled();
    expect(button).not.toHaveAttribute("aria-busy");

    await userEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("while pending it is disabled, marked busy, shows the pending label and a spinner", () => {
    const { container } = render(
      <PendingButton pending pendingLabel="Deleting…">
        Delete
      </PendingButton>,
    );

    const button = screen.getByRole("button", { name: /deleting/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(container.querySelector(".spinner")).toBeInTheDocument();
  });

  it("does not fire its handler again while pending", async () => {
    const onClick = vi.fn();
    render(
      <PendingButton pending pendingLabel="Deleting…" onClick={onClick}>
        Delete
      </PendingButton>,
    );

    // `pointerEvents: none` from the disabled state would make a plain click throw, so
    // this asserts on the handler rather than on the click being possible.
    await userEvent.click(screen.getByRole("button", { name: /deleting/i }), { pointerEventsCheck: 0 });
    expect(onClick).not.toHaveBeenCalled();
  });

  describe('as="span" (a trigger nested inside a link)', () => {
    it("uses aria-disabled, stays focusable, and swallows the click so the link does not follow", async () => {
      const onClick = vi.fn();
      const onNavigate = vi.fn((event) => event.preventDefault());

      render(
        // eslint-disable-next-line jsx-a11y/anchor-is-valid
        <a href="/somewhere" onClick={onNavigate}>
          <PendingButton as="span" role="button" tabIndex={0} pending pendingLabel="Deleting…" onClick={onClick}>
            Delete
          </PendingButton>
        </a>,
      );

      const trigger = screen.getByRole("button", { name: /deleting/i });
      expect(trigger).toHaveAttribute("aria-disabled", "true");
      // Still reachable by keyboard: a natively disabled control would drop out of the
      // tab order mid-interaction.
      expect(trigger).toHaveAttribute("tabindex", "0");

      await userEvent.click(trigger);
      expect(onClick).not.toHaveBeenCalled();
      expect(onNavigate).not.toHaveBeenCalled();
    });
  });
});
