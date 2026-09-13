import { render, screen } from "@testing-library/react";
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
});
