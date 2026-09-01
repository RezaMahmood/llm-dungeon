import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AdventureList from "../../../src/components/GameSetup/AdventureList.jsx";

describe("AdventureList", () => {
  it("shows the empty-state message when no adventures are published (FR-006)", () => {
    render(<AdventureList adventures={[]} loading={false} error={null} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText(/no adventures are published yet/i)).toBeInTheDocument();
  });

  it("renders each published adventure distinguishable by name (FR-001)", () => {
    render(
      <AdventureList
        adventures={[
          { id: "a1", name: "Nine Doors of Mudlark Hall", tone: "Mystery", sessionLengthMinutes: 20, readingLevel: "Year 5" },
          { id: "a2", name: "The Balloon Post", tone: "Adventure", sessionLengthMinutes: 15, readingLevel: "Year 4" },
        ]}
        loading={false}
        error={null}
        selectedId={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByText("Nine Doors of Mudlark Hall")).toBeInTheDocument();
    expect(screen.getByText("The Balloon Post")).toBeInTheDocument();
  });

  it("calls onSelect with the adventure id when a card is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <AdventureList
        adventures={[{ id: "a1", name: "Nine Doors of Mudlark Hall" }]}
        loading={false}
        error={null}
        selectedId={null}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByText("Nine Doors of Mudlark Hall"));

    expect(onSelect).toHaveBeenCalledWith("a1");
  });
});
