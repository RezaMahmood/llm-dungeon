import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CharacterNameStep from "../../../src/components/GameSetup/CharacterNameStep.jsx";

describe("CharacterNameStep", () => {
  it("caps input at 50 characters via maxLength", () => {
    render(<CharacterNameStep value="" onChange={() => {}} error={null} />);

    expect(screen.getByLabelText(/character name/i)).toHaveAttribute("maxLength", "50");
  });

  it("calls onChange as the player types", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CharacterNameStep value="" onChange={onChange} error={null} />);

    await user.type(screen.getByLabelText(/character name/i), "Wren");

    expect(onChange).toHaveBeenCalled();
  });

  it("shows a server-identified error message (blank name, FR-002/FR-005)", () => {
    render(<CharacterNameStep value="" onChange={() => {}} error="Character name is required." />);

    expect(screen.getByRole("alert")).toHaveTextContent("Character name is required.");
  });
});
