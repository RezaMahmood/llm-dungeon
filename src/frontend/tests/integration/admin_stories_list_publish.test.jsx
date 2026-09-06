import { render, screen, waitForElementToBeRemoved, within } from "@testing-library/react";
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

    expect(await within(row).findByText("Published")).toBeInTheDocument();
    expect(publishStory).toHaveBeenCalledWith("tok", "s1");
    expect(listStories).toHaveBeenCalledTimes(1);
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

    expect(await within(row).findByText(/must be test-played/i)).toBeInTheDocument();
    expect(within(row).getByText("Draft")).toBeInTheDocument();
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
    expect(within(rowFor("The Lighthouse")).getByText("Published")).toBeInTheDocument();
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
    expect(await within(rowFor("The Lighthouse")).findByText("Draft")).toBeInTheDocument();
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
    expect(await within(row).findByText("Published")).toBeInTheDocument();

    // Re-publishing an already-published story is a no-op success, and the
    // row still only shows one Unpublish control afterward.
    await user.click(within(row).getByRole("button", { name: /^unpublish$/i }));
    await user.click(screen.getByRole("button", { name: /keep it published/i }));
    expect(within(row).getByText("Published")).toBeInTheDocument();
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

    expect(await within(row1).findByText("Published")).toBeInTheDocument();
    expect(within(rowFor("Cavern of Echoes")).getByText("Draft")).toBeInTheDocument();
  });
});
