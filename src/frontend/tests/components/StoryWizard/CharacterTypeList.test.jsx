import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CharacterTypeList from "../../../src/components/Admin/StoryWizard/CharacterTypeList.jsx";

describe("CharacterTypeList", () => {
  it("keeps a just-added, uncommitted row when the parent re-renders with unrelated but content-identical characterTypes (regression)", async () => {
    // The wizard replaces the whole draft object (a fresh `characterTypes` array
    // reference every time, even when its content hasn't changed) on every write —
    // including ones for other fields, like a message response arriving while the
    // admin is mid-edit here. Resetting local rows on prop *reference* alone wiped an
    // in-progress "Add character type" row the moment any concurrent write landed.
    const onChange = vi.fn();
    const { rerender } = render(<CharacterTypeList characterTypes={[]} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /add character type/i }));
    expect(screen.getByLabelText(/character name/i)).toBeInTheDocument();

    // A new array instance, same (empty) content — simulates an unrelated draft refresh.
    rerender(<CharacterTypeList characterTypes={[]} onChange={onChange} />);

    expect(screen.getByLabelText(/character name/i)).toBeInTheDocument();
  });

  it("does resync when characterTypes genuinely changes remotely", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<CharacterTypeList characterTypes={[]} onChange={onChange} />);

    rerender(<CharacterTypeList characterTypes={[{ name: "Curious Cousin", description: "" }]} onChange={onChange} />);

    expect(screen.getByDisplayValue("Curious Cousin")).toBeInTheDocument();
  });

  it("renders existing character type rows", () => {
    render(
      <CharacterTypeList
        characterTypes={[{ name: "Curious Cousin", description: "Visiting for the summer." }]}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByDisplayValue("Curious Cousin")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Visiting for the summer.")).toBeInTheDocument();
  });

  it("adds a row locally, then commits it once a name is entered and blurred", async () => {
    const onChange = vi.fn();
    render(<CharacterTypeList characterTypes={[]} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /add character type/i }));
    expect(onChange).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText(/character name/i), "Local Kid");
    await userEvent.tab();

    expect(onChange).toHaveBeenCalledWith([{ name: "Local Kid", description: "" }]);
  });

  it("removes a row immediately", async () => {
    const onChange = vi.fn();
    render(
      <CharacterTypeList
        characterTypes={[
          { name: "Curious Cousin", description: "" },
          { name: "Local Kid", description: "" },
        ]}
        onChange={onChange}
      />,
    );

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    await userEvent.click(removeButtons[0]);

    expect(onChange).toHaveBeenCalledWith([{ name: "Local Kid", description: "" }]);
  });
});
