import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StoryPane from "../../src/components/Play/StoryPane.jsx";

describe("StoryPane (008-core-gameplay)", () => {
  it("renders each turn's narrative, oldest first", () => {
    render(
      <StoryPane
        turns={[
          { turnNumber: 0, narrativeText: "The door creaks open.", playerInput: null },
          { turnNumber: 1, narrativeText: "You step inside.", playerInput: "step inside" },
        ]}
      />,
    );

    expect(screen.getByText("The door creaks open.")).toBeInTheDocument();
    expect(screen.getByText("step inside")).toBeInTheDocument();
    expect(screen.getByText("You step inside.")).toBeInTheDocument();
  });

  it("omits the player-input row for the opening turn", () => {
    render(<StoryPane turns={[{ turnNumber: 0, narrativeText: "The door creaks open.", playerInput: null }]} />);

    expect(screen.queryByText("You")).not.toBeInTheDocument();
  });
});
