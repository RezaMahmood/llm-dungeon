import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CharacterTypeStep from "../../../src/components/GameSetup/CharacterTypeStep.jsx";

describe("CharacterTypeStep", () => {
  it("shows a single character type as an explicit choice, not pre-selected (edge case)", () => {
    render(
      <CharacterTypeStep
        characterTypes={[{ name: "Detective", description: "Sharp-eyed." }]}
        loading={false}
        error={null}
        selectedName={null}
        onSelect={() => {}}
      />,
    );

    const radio = screen.getByRole("radio", { name: /detective/i });
    expect(radio).toBeInTheDocument();
    expect(radio).not.toBeChecked();
  });

  it("renders every character type for the selected adventure and lets the player choose one", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <CharacterTypeStep
        characterTypes={[
          { name: "Detective", description: "Sharp-eyed." },
          { name: "Ghost", description: "Already knows every room." },
        ]}
        loading={false}
        error={null}
        selectedName={null}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByRole("radio", { name: /detective/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /ghost/i })).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: /ghost/i }));

    expect(onSelect).toHaveBeenCalledWith("Ghost");
  });
});
