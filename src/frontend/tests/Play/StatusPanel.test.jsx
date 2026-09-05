import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StatusPanel from "../../src/components/Play/StatusPanel.jsx";

describe("StatusPanel (008-core-gameplay)", () => {
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
});
