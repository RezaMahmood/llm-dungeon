import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import StoryPane from "../../src/components/Play/StoryPane.jsx";

/** jsdom never lays anything out, so every element's real scrollHeight is always 0 —
 * that would make a "scrolled to the bottom" assertion trivially true whether or not
 * the component actually scrolls. Stubbing scrollHeight at the prototype level, before
 * the component mounts, gives the auto-scroll effect something non-zero to copy into
 * scrollTop (029, FR-004), so the assertion actually distinguishes "scrolled" from
 * "never touched". */
let scrollHeightValue = 0;

function mockScrollHeight() {
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
    configurable: true,
    get: () => scrollHeightValue,
  });
}

afterEach(() => {
  delete HTMLElement.prototype.scrollHeight;
});

describe("StoryPane (008-core-gameplay-done)", () => {
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

  it("sets player entries in italics and story entries roman (029, FR-003)", () => {
    render(
      <StoryPane
        turns={[
          { turnNumber: 0, narrativeText: "The door creaks open.", playerInput: null },
          { turnNumber: 1, narrativeText: "You step inside.", playerInput: "step inside" },
        ]}
      />,
    );

    expect(screen.getByText("step inside")).toHaveClass("play-text-player");
    expect(screen.getByText("The door creaks open.")).not.toHaveClass("play-text-player");
    expect(screen.getByText("You step inside.")).not.toHaveClass("play-text-player");
  });

  it("scrolls to the newest content on mount (029, FR-004)", () => {
    scrollHeightValue = 900;
    mockScrollHeight();

    const { container } = render(
      <StoryPane turns={[{ turnNumber: 0, narrativeText: "The door creaks open.", playerInput: null }]} />,
    );

    expect(container.querySelector(".storyscroll").scrollTop).toBe(900);
  });

  it("scrolls to the newest content whenever a turn is appended (029, FR-004)", () => {
    scrollHeightValue = 300;
    mockScrollHeight();
    const turns = [{ turnNumber: 0, narrativeText: "The door creaks open.", playerInput: null }];
    const { container, rerender } = render(<StoryPane turns={turns} />);

    scrollHeightValue = 1200;
    rerender(
      <StoryPane
        turns={[
          ...turns,
          { turnNumber: 1, narrativeText: "You step inside.", playerInput: "step inside" },
        ]}
      />,
    );

    expect(container.querySelector(".storyscroll").scrollTop).toBe(1200);
  });

  it("renders the chapter numeral and kicker when the latest turn reports progress (029, FR-002)", () => {
    render(
      <StoryPane
        turns={[
          {
            turnNumber: 0,
            narrativeText: "A spiral of stairs climbs into the dark.",
            playerInput: null,
            locationLabel: "The keeper's stairs",
            progress: { current: 3, total: 5 },
          },
        ]}
      />,
    );

    expect(screen.getByText("03")).toBeInTheDocument();
    expect(screen.getByText("Chapter three — The keeper's stairs")).toBeInTheDocument();
  });

  it("renders neither the numeral nor the kicker when the latest turn reports no progress (029, FR-002)", () => {
    render(
      <StoryPane
        turns={[
          {
            turnNumber: 0,
            narrativeText: "The door creaks open.",
            playerInput: null,
            locationLabel: "Lighthouse entrance",
            progress: null,
          },
        ]}
      />,
    );

    expect(screen.queryByText(/^chapter /i)).not.toBeInTheDocument();
  });
});
