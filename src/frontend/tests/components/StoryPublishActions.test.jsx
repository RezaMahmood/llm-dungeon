import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const publishStory = vi.fn();
const unpublishStory = vi.fn();

vi.mock("../../src/services/storyDraftService.js", () => ({
  publishStory: (...args) => publishStory(...args),
  unpublishStory: (...args) => unpublishStory(...args),
}));

import StoryPublishActions from "../../src/components/Admin/StoryPublishActions.jsx";

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

describe("StoryPublishActions (005 FR-010/FR-011/FR-013, extracted per research.md §11)", () => {
  beforeEach(() => {
    publishStory.mockReset();
    unpublishStory.mockReset();
  });

  it("renders the current published state", () => {
    render(<StoryPublishActions story={UNPUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);
    expect(screen.getByText(/unpublished/i)).toBeInTheDocument();
  });

  it("requires confirmation before publishing (amended 005 FR-013) — no request until confirmed", async () => {
    render(<StoryPublishActions story={UNPUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(publishStory).not.toHaveBeenCalled();
  });

  it("shows the FR-011 gate explanation and does not flip published when the gate blocks publish", async () => {
    publishStory.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { error: "test_play_required", message: "This story must be test-played since its last content change before it can be published." },
      },
    });
    const onStoryChange = vi.fn();
    render(<StoryPublishActions story={UNPUBLISHED_STORY} token="tok" onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    expect(await screen.findByText(/must be test-played/i)).toBeInTheDocument();
    expect(onStoryChange).not.toHaveBeenCalled();
  });

  it("confirming the dialog calls publishStory and reflects published:true when the gate is satisfied", async () => {
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { ...UNPUBLISHED_STORY, published: true, lastPublishedAt: "2026-08-30T14:22:00Z" },
    });
    const onStoryChange = vi.fn();
    render(<StoryPublishActions story={UNPUBLISHED_STORY} token="tok" onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    expect(publishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(onStoryChange).toHaveBeenCalledWith(expect.objectContaining({ published: true }));
  });

  it("calls the optional onPublished callback after a confirmed publish succeeds (010-story-test-play-done)", async () => {
    const publishedStory = { ...UNPUBLISHED_STORY, published: true, lastPublishedAt: "2026-08-30T14:22:00Z" };
    publishStory.mockResolvedValueOnce({ status: "success", story: publishedStory });
    const onPublished = vi.fn();
    render(
      <StoryPublishActions story={UNPUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} onPublished={onPublished} />
    );

    await userEvent.click(screen.getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    expect(onPublished).toHaveBeenCalledWith(expect.objectContaining({ published: true }));
  });

  it("requires confirmation before unpublishing (005 FR-013)", async () => {
    render(<StoryPublishActions story={PUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(unpublishStory).not.toHaveBeenCalled();
  });

  it("confirming the dialog calls unpublishStory and reflects published:false", async () => {
    unpublishStory.mockResolvedValueOnce({ status: "success", story: { ...PUBLISHED_STORY, published: false } });
    const onStoryChange = vi.fn();
    render(<StoryPublishActions story={PUBLISHED_STORY} token="tok" onStoryChange={onStoryChange} />);

    await userEvent.click(screen.getByRole("button", { name: /^unpublish$/i }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: /^unpublish$/i }));

    expect(unpublishStory).toHaveBeenCalledWith("tok", "story-1");
    expect(onStoryChange).toHaveBeenCalledWith(expect.objectContaining({ published: false }));
  });

  // --- hideStatusLine (026-token-usage research.md Decision 8) ---

  it("renders the inline status/last-published line by default", () => {
    render(<StoryPublishActions story={PUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} />);

    expect(screen.getByText(/last published/i)).toBeInTheDocument();
  });

  it("suppresses the inline status/last-published line when hideStatusLine is set", () => {
    render(<StoryPublishActions story={PUBLISHED_STORY} token="tok" onStoryChange={vi.fn()} hideStatusLine />);

    expect(screen.queryByText(/status:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/last published/i)).not.toBeInTheDocument();
    // The publish/unpublish control itself is unaffected.
    expect(screen.getByRole("button", { name: /^unpublish$/i })).toBeInTheDocument();
  });
});
