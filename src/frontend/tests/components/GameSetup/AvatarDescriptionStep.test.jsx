import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AvatarDescriptionStep from "../../../src/components/GameSetup/AvatarDescriptionStep.jsx";

describe("AvatarDescriptionStep", () => {
  it("renders no character-type choice — a free-text description only (FR-002)", () => {
    render(<AvatarDescriptionStep value="" onChange={() => {}} error={null} disabled={false} />);

    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/describe your character/i)).toBeInTheDocument();
  });

  it("reports typed text back to the caller", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<AvatarDescriptionStep value="" onChange={onChange} error={null} disabled={false} />);

    await user.type(screen.getByLabelText(/describe your character/i), "A");

    expect(onChange).toHaveBeenCalledWith("A");
  });

  it("shows a field error when supplied", () => {
    render(
      <AvatarDescriptionStep value="a knight" onChange={() => {}} error="Say a bit more about your character." disabled={false} />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Say a bit more about your character.");
  });

  it("disables the textarea while a check is pending (FR-013)", () => {
    render(<AvatarDescriptionStep value="A curious cousin exploring the cove." onChange={() => {}} error={null} disabled />);

    expect(screen.getByLabelText(/describe your character/i)).toBeDisabled();
  });
});
