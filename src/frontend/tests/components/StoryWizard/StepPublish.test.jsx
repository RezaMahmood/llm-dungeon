import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const publishStory = vi.fn();
const unpublishStory = vi.fn();

vi.mock("../../../src/services/storyDraftService.js", () => ({
  publishStory: (...args) => publishStory(...args),
  unpublishStory: (...args) => unpublishStory(...args),
}));

import StepPublish from "../../../src/components/Admin/StoryWizard/StepPublish.jsx";

const UNPUBLISHED_STORY = {
  id: "story-1",
  name: "The Lighthouse at Gullwing Cove",
  published: false,
  lastPublishedAt: null,
};

const PUBLISHED_STORY = {
  id: "story-1",
  name: "The Lighthouse at Gullwing Cove",
  published: true,
  lastPublishedAt: "2026-08-30T14:22:00Z",
};

describe("StepPublish", () => {
  beforeEach(() => {
    publishStory.mockReset();
    unpublishStory.mockReset();
  });

  it("renders the current published state", () => {
    render(<StepPublish story={UNPUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);
    expect(screen.getByText(/unpublished/i)).toBeInTheDocument();
  });

  it("shows the FR-011 explanatory text and does not flip published when the gate blocks publish", async () => {
    publishStory.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { error: "test_play_required", message: "This story must be test-played since its last content change before it can be published." },
      },
    });
    const onStoryChange = vi.fn();
    render(<StepPublish story={UNPUBLISHED_STORY} token="tok" onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    expect(await screen.findByText(/must be test-played/i)).toBeInTheDocument();
    expect(onStoryChange).not.toHaveBeenCalled();
    expect(screen.getByText(/unpublished/i)).toBeInTheDocument();
  });

  it("calls publishStory and reflects published:true when the gate is satisfied", async () => {
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...UNPUBLISHED_STORY, published: true, lastPublishedAt: "2026-08-30T14:22:00Z" },
    });
    const onStoryChange = vi.fn();
    render(<StepPublish story={UNPUBLISHED_STORY} token="tok" onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    expect(publishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(onStoryChange).toHaveBeenCalledWith(expect.objectContaining({ published: true }));
  });

  it("opens the confirmation dialog on Unpublish and does not call unpublishStory until confirmed", async () => {
    render(<StepPublish story={PUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(unpublishStory).not.toHaveBeenCalled();
  });

  it("confirming the dialog calls unpublishStory and reflects published:false", async () => {
    unpublishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...PUBLISHED_STORY, published: false },
    });
    const onStoryChange = vi.fn();
    render(<StepPublish story={PUBLISHED_STORY} token="tok" onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^unpublish$/i }));

    expect(unpublishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(onStoryChange).toHaveBeenCalledWith(expect.objectContaining({ published: false }));
  });

  it("canceling the dialog leaves state unchanged", async () => {
    render(<StepPublish story={PUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));
    await userEvent.click(screen.getByRole("button", { name: /keep it published/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(unpublishStory).not.toHaveBeenCalled();
  });
});
