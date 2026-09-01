import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import StepPublish from "../../../src/components/Admin/StoryWizard/StepPublish.jsx";
import { publishStory, unpublishStory } from "../../../src/services/storyDraftService.js";

vi.mock("../../../src/services/storyDraftService.js", () => ({
  publishStory: vi.fn(),
  unpublishStory: vi.fn(),
}));

const UNPUBLISHED_STORY = { id: "story-1", published: false, lastPublishedAt: null };
const PUBLISHED_STORY = { id: "story-1", published: true, lastPublishedAt: "2026-08-30T14:22:00Z" };

describe("StepPublish", () => {
  beforeEach(() => {
    publishStory.mockReset();
    unpublishStory.mockReset();
  });

  it("publishes and reports the story back once the gate is satisfied", async () => {
    const onStoryChange = vi.fn();
    publishStory.mockResolvedValue({ status: "success", story: PUBLISHED_STORY });
    render(<StepPublish token="tok" story={UNPUBLISHED_STORY} onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    expect(publishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(onStoryChange).toHaveBeenCalledWith(PUBLISHED_STORY);
  });

  it("shows the server's blocked-explanation text on a 409 (FR-011)", async () => {
    publishStory.mockRejectedValue({
      response: { status: 409, data: { error: "test_play_required", message: "This story must be test-played first." } },
    });
    render(<StepPublish token="tok" story={UNPUBLISHED_STORY} onStoryChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    expect(await screen.findByText("This story must be test-played first.")).toBeInTheDocument();
  });

  it("requires confirmation before sending the unpublish request (FR-013)", async () => {
    const onStoryChange = vi.fn();
    unpublishStory.mockResolvedValue({ status: "success", story: { ...PUBLISHED_STORY, published: false } });
    render(<StepPublish token="tok" story={PUBLISHED_STORY} onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));
    expect(unpublishStory).not.toHaveBeenCalled();
    expect(screen.getByText(/are you sure/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /yes, unpublish/i }));

    expect(unpublishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(onStoryChange).toHaveBeenCalled();
  });

  it("cancelling the confirmation does not call unpublish", async () => {
    render(<StepPublish token="tok" story={PUBLISHED_STORY} onStoryChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(unpublishStory).not.toHaveBeenCalled();
    expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
  });
});
