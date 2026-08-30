import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CharacterTypeList from "../../../src/components/Admin/StoryWizard/CharacterTypeList.jsx";

describe("CharacterTypeList", () => {
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
