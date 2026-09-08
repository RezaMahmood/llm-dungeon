import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import IdeaPanel from "../../../src/components/Admin/StoryWizard/IdeaPanel.jsx";

describe("IdeaPanel", () => {
  it("sends the idea once and clears the input", async () => {
    const onSuggestWorldPrompt = vi.fn().mockResolvedValue(undefined);
    render(<IdeaPanel onSuggestWorldPrompt={onSuggestWorldPrompt} />);

    const input = screen.getByPlaceholderText(/describe your idea/i);
    await userEvent.type(input, "A lighthouse nobody has visited in years.");
    await userEvent.click(screen.getByRole("button", { name: /suggest world prompt/i }));

    expect(onSuggestWorldPrompt).toHaveBeenCalledTimes(1);
    expect(onSuggestWorldPrompt).toHaveBeenCalledWith("A lighthouse nobody has visited in years.");
    expect(input).toHaveValue("");
  });

  it("does not send an empty idea", async () => {
    const onSuggestWorldPrompt = vi.fn().mockResolvedValue(undefined);
    render(<IdeaPanel onSuggestWorldPrompt={onSuggestWorldPrompt} />);

    await userEvent.click(screen.getByRole("button", { name: /suggest world prompt/i }));

    expect(onSuggestWorldPrompt).not.toHaveBeenCalled();
  });

  it("surfaces an error and keeps the idea when the suggestion fails", async () => {
    const onSuggestWorldPrompt = vi.fn().mockRejectedValue(new Error("network error"));
    render(<IdeaPanel onSuggestWorldPrompt={onSuggestWorldPrompt} />);

    const input = screen.getByPlaceholderText(/describe your idea/i);
    await userEvent.type(input, "A lighthouse nobody has visited in years.");
    await userEvent.click(screen.getByRole("button", { name: /suggest world prompt/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(input).toHaveValue("A lighthouse nobody has visited in years.");
  });
});
