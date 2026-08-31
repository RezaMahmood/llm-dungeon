import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn();
const listStories = vi.fn();

// Stable references: a fresh `instance`/`accounts` object per render would
// re-create AdminPage's `refresh` callback every render and loop the effect.
const mockInstance = { acquireTokenSilent, logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "admin@example.com", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/services/storyDraftService.js", () => ({
  listStories: (...args) => listStories(...args),
}));

import AdminPage from "../../src/pages/AdminPage.jsx";

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/admin"]}>
      <AdminPage />
    </MemoryRouter>,
  );

const waitForLoad = () => waitForElementToBeRemoved(() => screen.queryByText(/loading stories/i));

describe("Admin stories list (FR-013, SC-007)", () => {
  beforeEach(() => {
    acquireTokenSilent.mockReset().mockResolvedValue({ accessToken: "tok" });
    listStories.mockReset();
  });

  it("lists each existing story with its name and status", async () => {
    listStories.mockResolvedValue({
      stories: [
        { id: "s1", name: "The Lighthouse", published: true, createdAt: "2026-08-01T00:00:00Z" },
        { id: "s2", name: "Cavern of Echoes", published: false, createdAt: "2026-08-02T00:00:00Z" },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("The Lighthouse")).toBeInTheDocument();
    expect(screen.getByText("Published")).toBeInTheDocument();
    expect(screen.getByText("Cavern of Echoes")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(listStories).toHaveBeenCalledWith("tok");
  });

  it("shows an empty state, not an error, when no stories exist yet", async () => {
    listStories.mockResolvedValue({ stories: [] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText(/no stories yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("is a distinct destination from the creation wizard", async () => {
    listStories.mockResolvedValue({ stories: [] });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("heading", { name: "Stories" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New story" })).toHaveAttribute(
      "href",
      "/admin/stories/new",
    );
  });

  it("offers a retry when the list cannot be loaded", async () => {
    const user = userEvent.setup();
    listStories.mockRejectedValueOnce(new Error("boom"));

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("alert")).toBeInTheDocument();

    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });
    await user.click(screen.getByRole("button", { name: /try again/i }));

    expect(await screen.findByText("The Lighthouse")).toBeInTheDocument();
  });

  it("renders a story with no name without breaking the row", async () => {
    listStories.mockResolvedValue({ stories: [{ id: "s1", name: null, published: false }] });

    renderPage();
    await waitForLoad();

    expect(screen.getByText("Untitled story")).toBeInTheDocument();
  });
});
