import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const deleteStory = vi.fn();

vi.mock("../../src/services/storyDraftService.js", () => ({
  deleteStory: (...args) => deleteStory(...args),
}));

import StoryDeleteAction from "../../src/components/Admin/StoryDeleteAction.jsx";

const STORY = {
  id: "story-1",
  name: "The Lighthouse at Gullwing Cove",
};

describe("StoryDeleteAction (025-story-delete-done FR-001, FR-002)", () => {
  beforeEach(() => {
    deleteStory.mockReset();
  });

  it("clicking Delete opens the confirmation dialog and does not call deleteStory until confirmed", async () => {
    render(<StoryDeleteAction story={STORY} token="tok" onDeleted={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(deleteStory).not.toHaveBeenCalled();
  });

  it("the dialog's copy states the action is permanent and irreversible", async () => {
    render(<StoryDeleteAction story={STORY} token="tok" onDeleted={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/permanent/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/cannot be undone/i)).toBeInTheDocument();
  });

  it("confirming calls deleteStory and invokes the deleted callback", async () => {
    deleteStory.mockResolvedValueOnce({ status: "deleted", storyId: "story-1" });
    const onDeleted = vi.fn();
    render(<StoryDeleteAction story={STORY} token="tok" onDeleted={onDeleted} />);

    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^delete$/i }));

    expect(deleteStory).toHaveBeenCalledWith("tok", "story-1");
    expect(await screen.findByRole("button", { name: /^delete$/i })).toBeInTheDocument();
    expect(onDeleted).toHaveBeenCalledWith("story-1");
  });

  it("canceling leaves state unchanged and calls nothing", async () => {
    const onDeleted = vi.fn();
    render(<StoryDeleteAction story={STORY} token="tok" onDeleted={onDeleted} />);

    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await userEvent.click(screen.getByRole("button", { name: /keep it/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteStory).not.toHaveBeenCalled();
    expect(onDeleted).not.toHaveBeenCalled();
  });
});
