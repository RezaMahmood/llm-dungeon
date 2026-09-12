import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listStories = vi.fn();
const publishStory = vi.fn();
const unpublishStory = vi.fn();

// Stable references: a fresh `instance`/`accounts` object per render would
// re-create AdminPage's `refresh`/`getToken` callbacks every render and loop
// the effect.
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  listStories: (...args) => listStories(...args),
  publishStory: (...args) => publishStory(...args),
  unpublishStory: (...args) => unpublishStory(...args),
}));

import AdminPage from "../../src/pages/AdminPage.jsx";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin"]}>
      <AdminPage />
    </MemoryRouter>,
  );

const waitForLoad = () => waitForElementToBeRemoved(() => screen.queryByText(/loading stories/i));

const rowFor = (name) => screen.getByText(name).closest("tr");

// Status now renders twice per row by design (012-story-editing-and-review): the status
// tag, plus the shared StoryPublishActions control's own "Status: …" line. Scope to the
// tag specifically rather than an ambiguous text match.
const statusTag = (row) => row.querySelector(".tag");

describe("Admin stories list publish/unpublish (FR-007, FR-010, FR-011, FR-013, FR-014, FR-016)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listStories.mockReset();
    publishStory.mockReset();
    unpublishStory.mockReset();
  });

  it("publishes an unpublished row and flips it to Published without refetching the list", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { id: "s1", name: "The Lighthouse", published: true, lastPublishedAt: "2026-09-06T00:00:00Z" },
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    await waitFor(() => expect(statusTag(row)).toHaveTextContent("Published"));
    expect(publishStory).toHaveBeenCalledWith("tok", "s1");
    expect(listStories).toHaveBeenCalledTimes(1);
  });

  it("requires confirmation before publishing and does not call publishStory until confirmed", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^publish$/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(publishStory).not.toHaveBeenCalled();
  });

  it("shows the FR-011 explanatory text and leaves the row unchanged on a 409", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });
    publishStory.mockRejectedValueOnce({
      response: { status: 409, data: { message: "This story must be test-played before it can be published." } },
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    expect(await within(row).findByText(/must be test-played/i)).toBeInTheDocument();
    expect(statusTag(row)).toHaveTextContent("Unpublished");
  });

  it("requires confirmation before unpublishing and does not call unpublishStory until confirmed", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: true }],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^unpublish$/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(unpublishStory).not.toHaveBeenCalled();
  });

  it("canceling the confirmation changes nothing", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: true }],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^unpublish$/i }));
    await user.click(screen.getByRole("button", { name: /keep it published/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(unpublishStory).not.toHaveBeenCalled();
    expect(statusTag(rowFor("The Lighthouse"))).toHaveTextContent("Published");
  });

  it("confirming unpublishes and updates just that row in place", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: true }],
    });
    unpublishStory.mockResolvedValueOnce({
      status: "success",
      story: { id: "s1", name: "The Lighthouse", published: false, lastPublishedAt: "2026-09-01T00:00:00Z" },
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^unpublish$/i }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^unpublish$/i }));

    expect(unpublishStory).toHaveBeenCalledWith("tok", "s1");
    await waitFor(() => expect(statusTag(rowFor("The Lighthouse"))).toHaveTextContent("Unpublished"));
    expect(listStories).toHaveBeenCalledTimes(1);
  });

  it("a redundant publish succeeds idempotently", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });
    publishStory.mockResolvedValue({
      status: "success",
      story: { id: "s1", name: "The Lighthouse", published: true, lastPublishedAt: "2026-09-06T00:00:00Z" },
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^publish$/i }));
    let dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^publish$/i }));
    await waitFor(() => expect(statusTag(row)).toHaveTextContent("Published"));

    // Re-publishing an already-published story is a no-op success, and the
    // row still only shows one Unpublish control afterward.
    await user.click(within(row).getByRole("button", { name: /^unpublish$/i }));
    await user.click(screen.getByRole("button", { name: /keep it published/i }));
    expect(statusTag(row)).toHaveTextContent("Published");
  });

  it("only updates the acted-on row when several stories are listed", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [
        { id: "s1", name: "The Lighthouse", published: false },
        { id: "s2", name: "Cavern of Echoes", published: false },
      ],
    });
    publishStory.mockResolvedValueOnce({
      status: "success",
      story: { id: "s1", name: "The Lighthouse", published: true, lastPublishedAt: "2026-09-06T00:00:00Z" },
    });

    renderPage();
    await waitForLoad();

    const row1 = rowFor("The Lighthouse");
    await user.click(within(row1).getByRole("button", { name: /^publish$/i }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^publish$/i }));

    await waitFor(() => expect(statusTag(row1)).toHaveTextContent("Published"));
    expect(statusTag(rowFor("Cavern of Echoes"))).toHaveTextContent("Unpublished");
  });

  // --- Last-published date moves to a hover, not an always-visible line (026-token-usage
  // FR-005, FR-006, FR-007, Edge Cases) ---

  it("shows no inline last-published text, only a hover title, for a published story", async () => {
    listStories.mockResolvedValue({
      stories: [
        { id: "s1", name: "The Lighthouse", published: true, lastPublishedAt: "2026-09-01T12:00:00Z" },
      ],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    expect(row).not.toHaveTextContent(/last published/i);
    expect(statusTag(row)).toHaveAttribute("title", expect.stringContaining("2026"));
  });

  it("carries the hover date for a story unpublished after being published before", async () => {
    listStories.mockResolvedValue({
      stories: [
        { id: "s1", name: "The Lighthouse", published: false, lastPublishedAt: "2026-09-01T12:00:00Z" },
      ],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    expect(statusTag(row)).toHaveAttribute("title", expect.stringContaining("2026"));
  });

  it("has no hover title at all for a story that has never been published", async () => {
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    expect(statusTag(row)).not.toHaveAttribute("title");
  });
});
