import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import StatusPanel from "../../src/components/Play/StatusPanel.jsx";

describe("StatusPanel (008-core-gameplay-done)", () => {
  it("renders location, goal, and progress from the latest turn", () => {
    render(
      <StatusPanel
        locationLabel="The keeper's stairs"
        goalLabel="Find out who lit the lamp"
        progress={{ current: 3, total: 5 }}
        completionReason={null}
      />,
    );

    expect(screen.getByText("The keeper's stairs")).toBeInTheDocument();
    expect(screen.getByText("Find out who lit the lamp")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText(/of 5 chapters/i)).toBeInTheDocument();
  });

  it("shows the ending reason when the session has concluded", () => {
    render(
      <StatusPanel
        locationLabel="The cove"
        goalLabel={null}
        progress={null}
        completionReason={{ type: "success", detail: "the player escaped the cove" }}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/you succeeded/i);
    expect(screen.getByRole("status")).toHaveTextContent(/the player escaped the cove/i);
  });

  it("renders one segment per chapter, with the first `current` marked filled (029, FR-006)", () => {
    const { container } = render(
      <StatusPanel
        locationLabel="The keeper's stairs"
        goalLabel={null}
        progress={{ current: 3, total: 5 }}
        completionReason={null}
      />,
    );

    const segments = container.querySelectorAll(".progress-bars span");
    expect(segments).toHaveLength(5);
    expect(Array.from(segments).filter((span) => span.classList.contains("filled"))).toHaveLength(3);
    expect(segments[0]).toHaveClass("filled");
    expect(segments[1]).toHaveClass("filled");
    expect(segments[2]).toHaveClass("filled");
    expect(segments[3]).not.toHaveClass("filled");
    expect(segments[4]).not.toHaveClass("filled");
  });

  it("renders no segmented bar when there is no progress (029, FR-006)", () => {
    const { container } = render(
      <StatusPanel locationLabel="The cove" goalLabel={null} progress={null} completionReason={null} />,
    );

    expect(container.querySelectorAll(".progress-bars")).toHaveLength(0);
  });

  it("renders the hint control between the progress section and the autosave notice, inert but reachable (029, FR-007, US2 AS2)", async () => {
    const user = userEvent.setup();
    render(
      <StatusPanel
        locationLabel="The keeper's stairs"
        goalLabel={null}
        progress={{ current: 3, total: 5 }}
        completionReason={null}
      />,
    );

    const hint = screen.getByRole("button", { name: /stuck\? get a hint/i });
    // aria-disabled, never the native `disabled` attribute — a natively disabled button
    // drops out of the tab order and could never show a focus indicator (US2 AS2;
    // constitution, Interaction states).
    expect(hint).toHaveAttribute("aria-disabled", "true");
    expect(hint).not.toBeDisabled();
    expect(screen.getByText("Hints are coming soon.")).toBeInTheDocument();

    await user.tab();
    while (document.activeElement !== hint && document.activeElement !== document.body) {
      await user.tab();
    }
    expect(hint).toHaveFocus();

    await user.click(hint);
    // No handler, no state change — clicking it does nothing.
    expect(hint).toHaveAttribute("aria-disabled", "true");
  });

  it("keeps the hint control between progress and autosave even without progress data", () => {
    render(<StatusPanel locationLabel="The cove" goalLabel={null} progress={null} completionReason={null} />);

    expect(screen.getByRole("button", { name: /stuck\? get a hint/i })).toBeInTheDocument();
    expect(screen.getByText("Hints are coming soon.")).toBeInTheDocument();
  });

  it("shows the player's avatar description read-only, alongside location, goal, and progress (034, FR-001)", () => {
    render(
      <StatusPanel
        locationLabel="The keeper's stairs"
        goalLabel="Find out who lit the lamp"
        progress={{ current: 3, total: 5 }}
        completionReason={null}
        avatarDescription="A one-eyed lighthouse keeper's apprentice who fears the dark."
      />,
    );

    expect(
      screen.getByText("A one-eyed lighthouse keeper's apprentice who fears the dark."),
    ).toBeInTheDocument();
    expect(screen.getByText("The keeper's stairs")).toBeInTheDocument();
    expect(screen.getByText("Find out who lit the lamp")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders no avatar section when the session carries no description (034, FR-003)", () => {
    render(
      <StatusPanel
        locationLabel="The cove"
        goalLabel={null}
        progress={null}
        completionReason={null}
        avatarDescription={null}
      />,
    );

    expect(screen.queryByText(/who you are/i)).not.toBeInTheDocument();
  });
});
