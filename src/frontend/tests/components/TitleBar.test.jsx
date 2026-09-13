import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import TitleBar from "../../src/components/Layout/TitleBar.jsx";
import { PlayTitleProvider, usePublishPlayTitle } from "../../src/context/PlayTitleContext.jsx";
import { RefreshProvider, usePublishRefresh } from "../../src/context/RefreshContext.jsx";

const renderTitleBar = (props = {}) =>
  render(
    <MemoryRouter>
      <TitleBar {...props} />
    </MemoryRouter>,
  );

/** Renders with a real route so a fall-through navigation can be observed. */
const renderTitleBarWithRouting = (props = {}) =>
  render(
    <MemoryRouter initialEntries={["/game"]}>
      <Routes>
        <Route path="/menu" element={<p>story select</p>} />
        <Route path="/game" element={<TitleBar {...props} />} />
      </Routes>
    </MemoryRouter>,
  );

/** Publishes onSaveCheckpoint through PlayTitleContext, the way PlayPage does. */
function Publisher({ onSaveCheckpoint }) {
  usePublishPlayTitle({ storyTitle: "Story", onSaveCheckpoint });
  return null;
}

const renderTitleBarWithPublishedCheckpoint = (onSaveCheckpoint) =>
  render(
    <MemoryRouter>
      <PlayTitleProvider>
        <Publisher onSaveCheckpoint={onSaveCheckpoint} />
        <TitleBar />
      </PlayTitleProvider>
    </MemoryRouter>,
  );

/** Publishes { refresh, loading } through RefreshContext, the way PlayPage does
 * (019-spa-refresh-button — RefreshContext). */
function RefreshPublisher({ refresh, loading }) {
  usePublishRefresh({ refresh, loading });
  return null;
}

const renderTitleBarWithRefresh = ({ refresh = vi.fn(), loading = false } = {}) =>
  render(
    <MemoryRouter>
      <RefreshProvider>
        <RefreshPublisher refresh={refresh} loading={loading} />
        <TitleBar storyTitle="Story" />
      </RefreshProvider>
    </MemoryRouter>,
  );

describe("TitleBar (FR-006)", () => {
  it("renders the compact header content and no primary nav links", () => {
    renderTitleBar({ storyTitle: "The Lighthouse at Gullwing Cove", onSaveCheckpoint: vi.fn() });

    expect(screen.getByText("The Lighthouse at Gullwing Cove")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save a checkpoint/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pause & exit/i })).toBeInTheDocument();

    for (const label of ["Stories", "New story", "People", "My stories", "Badges"]) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });

  it("returns to story select from the brand mark", () => {
    renderTitleBar();
    expect(screen.getByRole("link", { name: "LLM Dungeon" })).toHaveAttribute("href", "/menu");
  });

  it("truncates a long story title rather than letting it push controls out of view", () => {
    renderTitleBar({ storyTitle: "A".repeat(300) });

    const title = screen.getByText("A".repeat(300));
    expect(title).toHaveClass("truncate");
    // Controls stay reachable alongside the overlong title.
    expect(screen.getByRole("button", { name: /pause & exit/i })).toBeInTheDocument();
  });

  it("adds no vertical chrome beyond the compact header, preserving reading area (SC-006)", () => {
    const { container } = renderTitleBar({ storyTitle: "Story" });
    const bar = container.firstChild;

    // Single-row flex header with token padding and a hairline rule — nothing
    // that would eat into the story pane below it.
    expect(bar).toHaveStyle({ display: "flex", alignItems: "center", flex: "none" });
    expect(bar.style.padding).toBe("var(--space-3) var(--space-4)");
  });

  it("calls the handlers the page supplies", async () => {
    const user = userEvent.setup();
    const onSaveCheckpoint = vi.fn();
    const onPauseExit = vi.fn();
    renderTitleBar({ storyTitle: "Story", onSaveCheckpoint, onPauseExit });

    await user.click(screen.getByRole("button", { name: /save a checkpoint/i }));
    await user.click(screen.getByRole("button", { name: /pause & exit/i }));

    expect(onSaveCheckpoint).toHaveBeenCalledOnce();
    expect(onPauseExit).toHaveBeenCalledOnce();
  });

  it("returns to story select on Pause & exit when the page supplies no handler yet", async () => {
    // PlayPage wires a real onPauseExit handler (008-core-gameplay-done); other
    // screens that render TitleBar without one must still fall back to this
    // default rather than a dead button (Principle IX final acceptance, Gate 7).
    const user = userEvent.setup();
    renderTitleBarWithRouting({ storyTitle: "Story" });

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));

    expect(screen.getByText("story select")).toBeInTheDocument();
  });

  it("hides the Save a checkpoint button when nothing is published (009-save-and-continue)", () => {
    renderTitleBar({ storyTitle: "Story" });

    expect(screen.queryByRole("button", { name: /save a checkpoint/i })).not.toBeInTheDocument();
  });

  it("invokes onSaveCheckpoint published via PlayTitleContext", async () => {
    const user = userEvent.setup();
    const onSaveCheckpoint = vi.fn();
    renderTitleBarWithPublishedCheckpoint(onSaveCheckpoint);

    await user.click(screen.getByRole("button", { name: /save a checkpoint/i }));

    expect(onSaveCheckpoint).toHaveBeenCalledOnce();
  });

  // --- 029-play-surface-design-spec (T023, US3): header Refresh control ---

  it("renders no refresh control when nothing is published (029)", () => {
    renderTitleBar({ storyTitle: "Story" });

    expect(screen.queryByRole("button", { name: /refresh/i })).not.toBeInTheDocument();
  });

  it("renders the published refresh control ahead of the other trailing actions and invokes it on click (029)", async () => {
    const user = userEvent.setup();
    const refresh = vi.fn();
    renderTitleBarWithRefresh({ refresh });

    const trailing = screen.getByRole("button", { name: /pause & exit/i }).closest('[data-nav-slot="trailing-actions"]');
    const buttons = within(trailing).getAllByRole("button");
    expect(buttons[0]).toHaveAccessibleName(/refresh/i);

    await user.click(screen.getByRole("button", { name: /^refresh$/i }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("disables the published refresh control while loading (029)", () => {
    renderTitleBarWithRefresh({ loading: true });

    const button = screen.getByRole("button", { name: /^refresh$/i });
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/refreshing/i);
  });
});
