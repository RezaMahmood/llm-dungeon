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
    expect(screen.getByText("Cavern of Echoes")).toBeInTheDocument();
    // Status is rendered twice per row by design (the status tag, plus the shared
    // StoryPublishActions control) — assert the tag specifically, by its class.
    expect(document.querySelector(".tag-accent")).toHaveTextContent("Published");
    expect(document.querySelector(".tag-neutral")).toHaveTextContent("Unpublished");
    expect(listStories).toHaveBeenCalledWith("tok");
  });

  it("gives every row a View affordance that navigates straight to its configuration view (FR-001, SC-001)", async () => {
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: true, createdAt: "2026-08-01T00:00:00Z" }],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("link", { name: /^view$/i })).toHaveAttribute("href", "/admin/stories/s1");
  });

  it("gives every row an Edit affordance pointing at the wizard's edit route (FR-005)", async () => {
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: true, createdAt: "2026-08-01T00:00:00Z" }],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("link", { name: /^edit$/i })).toHaveAttribute("href", "/admin/stories/s1/edit");
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

  // --- Accessibility (T043, FR-012 — the styling exception does not extend here) ---

  it("every row control is reachable by role and accessible name, and status reads as text", async () => {
    listStories.mockResolvedValue({
      stories: [
        { id: "s1", name: "The Lighthouse", published: true, createdAt: "2026-08-01T00:00:00Z" },
        { id: "s2", name: "Cavern of Echoes", published: false, createdAt: "2026-08-02T00:00:00Z" },
      ],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("heading", { name: "Stories" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    // Every row exposes View, Edit, and the shared publish/unpublish control by role.
    expect(screen.getAllByRole("link", { name: /^view$/i })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /^edit$/i })).toHaveLength(2);
    expect(screen.getByRole("button", { name: /^publish$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^unpublish$/i })).toBeInTheDocument();
    // Status is text content, not conveyed by color alone.
    expect(document.querySelector(".tag-accent").textContent).toBe("Published");
    expect(document.querySelector(".tag-neutral").textContent).toBe("Unpublished");
  });

  // --- Tokens column (026-token-usage FR-003, FR-004, FR-010) ---

  it("shows each story's cumulative token total formatted with thousands separators", async () => {
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: true, totalTokens: 48213 }],
    });

    renderPage();
    await waitForLoad();

    expect(screen.getByRole("columnheader", { name: "Tokens" })).toBeInTheDocument();
    expect(rowFor("The Lighthouse")).toHaveTextContent("48,213");
  });

  it("renders zero, not a blank cell, for a story with no tracked token usage", async () => {
    listStories.mockResolvedValue({
      stories: [{ id: "s1", name: "The Lighthouse", published: false }],
    });

    renderPage();
    await waitForLoad();

    expect(rowFor("The Lighthouse")).toHaveTextContent("0");
  });
});

function rowFor(name) {
  return screen.getByText(name).closest("tr");
}
