import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listStories = vi.fn();
const importStoryConfiguration = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  listStories: (...args) => listStories(...args),
  importStoryConfiguration: (...args) => importStoryConfiguration(...args),
}));

import AdminPage from "../../src/pages/AdminPage.jsx";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin"]}>
      <AdminPage />
    </MemoryRouter>,
  );

const waitForLoad = () => waitForElementToBeRemoved(() => screen.queryByText(/loading stories/i));

function jsonFile(content) {
  return new File([content], "story.json", { type: "application/json" });
}

describe("Admin story import flow (FR-005)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listStories.mockReset().mockResolvedValue({ stories: [] });
    importStoryConfiguration.mockReset();
  });

  it("uploads with overwrite confirmation and refreshes the list", async () => {
    renderPage();
    await waitForLoad();

    const payload = {
      id: "story-1",
      name: "The Sunken Library",
      worldPrompt: "A flooded library.",
      characterTypes: [{ name: "Archivist" }],
      completionCriteria: { successConditions: ["Recover the ledger"] },
    };
    const input = screen.getByLabelText(/upload configuration file/i);
    await userEvent.upload(input, jsonFile(JSON.stringify(payload)));

    expect(await screen.findByRole("dialog")).toHaveTextContent("story-1");

    importStoryConfiguration.mockResolvedValueOnce({ status: "updated", storyId: "story-1", story: {} });
    listStories.mockResolvedValue({
      stories: [{ id: "story-1", name: "The Sunken Library", published: false, createdAt: "2026-08-01T00:00:00Z" }],
    });
    await userEvent.click(screen.getByRole("button", { name: /^overwrite$/i }));

    expect(importStoryConfiguration).toHaveBeenCalledWith("tok", {
      configurationText: JSON.stringify(payload),
      confirmOverwriteStoryId: "story-1",
    });
    expect(await screen.findByText("The Sunken Library")).toBeInTheDocument();
  });

  it("uploads an id-less file with a supplied title", async () => {
    renderPage();
    await waitForLoad();

    const payload = {
      worldPrompt: "A flooded library.",
      characterTypes: [{ name: "Archivist" }],
      completionCriteria: { successConditions: ["Recover the ledger"] },
    };
    const input = screen.getByLabelText(/upload configuration file/i);
    await userEvent.upload(input, jsonFile(JSON.stringify(payload)));

    expect(await screen.findByText(/name this new story/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/title/i), "A Brand New Tale");

    importStoryConfiguration.mockResolvedValueOnce({ status: "created", storyId: "story-2", story: {} });
    await userEvent.click(screen.getByRole("button", { name: /create story/i }));

    expect(importStoryConfiguration).toHaveBeenCalledWith("tok", {
      configurationText: JSON.stringify(payload),
      title: "A Brand New Tale",
    });
  });

  it("shows the rejection message for a file that is not valid JSON", async () => {
    renderPage();
    await waitForLoad();

    const input = screen.getByLabelText(/upload configuration file/i);
    await userEvent.upload(input, jsonFile("{ not valid"));

    expect(await screen.findByText(/not valid json/i)).toBeInTheDocument();
    expect(importStoryConfiguration).not.toHaveBeenCalled();
  });

  it("shows the rejection message for an unmatched id (404)", async () => {
    renderPage();
    await waitForLoad();

    const payload = {
      id: "missing-id",
      name: "x",
      worldPrompt: "A flooded library.",
      characterTypes: [{ name: "Archivist" }],
      completionCriteria: { successConditions: ["Recover the ledger"] },
    };
    const input = screen.getByLabelText(/upload configuration file/i);
    await userEvent.upload(input, jsonFile(JSON.stringify(payload)));
    await screen.findByRole("dialog");

    importStoryConfiguration.mockRejectedValueOnce({
      response: {
        status: 404,
        data: { error: "story_not_found", message: "No story exists with the id in this file. Remove the id to upload it as a new story." },
      },
    });
    await userEvent.click(screen.getByRole("button", { name: /^overwrite$/i }));

    expect(await screen.findByText(/no story exists with the id/i)).toBeInTheDocument();
  });
});
