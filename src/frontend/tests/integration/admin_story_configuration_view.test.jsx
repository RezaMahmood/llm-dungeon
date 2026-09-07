import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const getStoryConfiguration = vi.fn();

const mockInstance = { acquireTokenSilent };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  getStoryConfiguration: (...args) => getStoryConfiguration(...args),
}));

import AdminStoryConfigurationPage from "../../src/pages/AdminStoryConfigurationPage.jsx";

const CONFIGURATION_TEXT = '{\n  "id": "story-1",\n  "name": "The Sunken Library",\n  "worldPrompt": "A flooded library."\n}\n';

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin/stories/story-1"]}>
      <Routes>
        <Route path="/admin/stories/:storyId" element={<AdminStoryConfigurationPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe("Admin story configuration viewer (FR-002, FR-004, SC-001)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    getStoryConfiguration.mockReset();

    // Blob/URL are not implemented by jsdom.
    global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("renders the response text verbatim", async () => {
    getStoryConfiguration.mockResolvedValue(CONFIGURATION_TEXT);

    renderPage();
    await waitForElementToBeRemoved(() => screen.queryByText(/loading configuration/i));

    expect(screen.getByText(/"worldPrompt": "A flooded library\."/)).toBeInTheDocument();
    expect(getStoryConfiguration).toHaveBeenCalledWith("tok", "story-1");
  });

  it("builds the Download Blob from the exact same text the viewer renders", async () => {
    getStoryConfiguration.mockResolvedValue(CONFIGURATION_TEXT);
    renderPage();
    await waitForElementToBeRemoved(() => screen.queryByText(/loading configuration/i));

    await userEvent.click(screen.getByRole("button", { name: /download/i }));

    expect(global.URL.createObjectURL).toHaveBeenCalledTimes(1);
    const blobArg = global.URL.createObjectURL.mock.calls[0][0];
    const blobText = await blobArg.text();
    expect(blobText).toBe(CONFIGURATION_TEXT);
  });

  it("offers a retry when the configuration cannot be loaded", async () => {
    getStoryConfiguration.mockRejectedValueOnce(new Error("boom"));
    renderPage();
    await waitForElementToBeRemoved(() => screen.queryByText(/loading configuration/i));

    expect(screen.getByRole("alert")).toBeInTheDocument();

    getStoryConfiguration.mockResolvedValue(CONFIGURATION_TEXT);
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));

    expect(await screen.findByText(/"worldPrompt"/)).toBeInTheDocument();
  });

  it("the configuration pane is a keyboard-focusable scroll region with an accessible name", async () => {
    getStoryConfiguration.mockResolvedValue(CONFIGURATION_TEXT);
    renderPage();
    await waitForElementToBeRemoved(() => screen.queryByText(/loading configuration/i));

    const region = screen.getByRole("region", { name: /story configuration file/i });
    expect(region).toHaveAttribute("tabindex", "0");
  });

  it("has a semantic heading and a Download control reachable by role and accessible name (T043)", async () => {
    getStoryConfiguration.mockResolvedValue(CONFIGURATION_TEXT);
    renderPage();
    await waitForElementToBeRemoved(() => screen.queryByText(/loading configuration/i));

    expect(screen.getByRole("heading", { name: /story configuration/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^download$/i })).toBeInTheDocument();
  });
});
