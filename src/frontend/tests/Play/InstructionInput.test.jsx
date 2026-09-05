import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import InstructionInput from "../../src/components/Play/InstructionInput.jsx";

describe("InstructionInput (008-core-gameplay)", () => {
  it("submits trimmed free-text input", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<InstructionInput onSubmit={onSubmit} disabled={false} />);

    await user.type(screen.getByLabelText(/what do you do next/i), "look around  ");
    await user.click(screen.getByRole("button", { name: /go/i }));

    expect(onSubmit).toHaveBeenCalledWith("look around");
  });

  it("does not submit blank input", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<InstructionInput onSubmit={onSubmit} disabled={false} />);

    await user.click(screen.getByRole("button", { name: /go/i }));

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables the input and submit button when disabled", () => {
    render(<InstructionInput onSubmit={vi.fn()} disabled />);

    expect(screen.getByLabelText(/what do you do next/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /go/i })).toBeDisabled();
  });
});
