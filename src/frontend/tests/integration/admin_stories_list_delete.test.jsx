import { render, screen, waitFor, waitForElementToBeRemoved, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listStories = vi.fn();
const publishStory = vi.fn();
const unpublishStory = vi.fn();
const deleteStory = vi.fn();

const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  listStories: (...args) => listStories(...args),
  publishStory: (...args) => publishStory(...args),
  unpublishStory: (...args) => unpublishStory(...args),
  deleteStory: (...args) => deleteStory(...args),
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

describe("Admin stories list delete (025-story-delete FR-001, FR-002, FR-012, SC-001, SC-004)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listStories.mockReset();
    publishStory.mockReset();
    unpublishStory.mockReset();
    deleteStory.mockReset();
  });

  it("deleting a row removes it from the rendered list in place, with no refetch of the full list", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });
    deleteStory.mockResolvedValueOnce({ status: "deleted", storyId: "s1" });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^delete$/i }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^delete$/i }));

    await waitFor(() => expect(screen.queryByText("The Lighthouse")).not.toBeInTheDocument());
    expect(deleteStory).toHaveBeenCalledWith("tok", "s1");
    expect(listStories).toHaveBeenCalledTimes(1);
  });

  it("cancelling the confirmation leaves the row in place and calls no API", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });

    renderPage();
    await waitForLoad();

    const row = rowFor("The Lighthouse");
    await user.click(within(row).getByRole("button", { name: /^delete$/i }));
    await user.click(screen.getByRole("button", { name: /keep it/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(deleteStory).not.toHaveBeenCalled();
    expect(screen.getByText("The Lighthouse")).toBeInTheDocument();
  });

  it("only the acted-on row is affected when several stories are listed", async () => {
    const user = userEvent.setup();
    listStories.mockResolvedValue({
      stories: [
        { id: "s1", name: "The Lighthouse", published: false },
        { id: "s2", name: "Cavern of Echoes", published: false },
      ],
    });
    deleteStory.mockResolvedValueOnce({ status: "deleted", storyId: "s1" });

    renderPage();
    await waitForLoad();

    const row1 = rowFor("The Lighthouse");
    await user.click(within(row1).getByRole("button", { name: /^delete$/i }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /^delete$/i }));

    await waitFor(() => expect(screen.queryByText("The Lighthouse")).not.toBeInTheDocument());
    expect(screen.getByText("Cavern of Echoes")).toBeInTheDocument();
  });
});
