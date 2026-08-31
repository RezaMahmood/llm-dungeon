import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import TitleBar from "../../src/components/Layout/TitleBar.jsx";

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

describe("TitleBar (FR-006)", () => {
  it("renders the compact header content and no primary nav links", () => {
    renderTitleBar({ storyTitle: "The Lighthouse at Gullwing Cove" });

    expect(screen.getByText("The Lighthouse at Gullwing Cove")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save a checkpoint/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pause & exit/i })).toBeInTheDocument();

    for (const label of ["Stories", "New story", "People", "My stories", "Badges"]) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });

  it("returns to story select from the brand mark", () => {
    renderTitleBar();
    expect(screen.getByRole("link", { name: "Lantern" })).toHaveAttribute("href", "/menu");
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
    // GamePage doesn't wire onPauseExit until 008-core-gameplay builds real
    // pause behavior — until then this must not be a dead button (found in
    // Principle IX final acceptance, Gate 7).
    const user = userEvent.setup();
    renderTitleBarWithRouting({ storyTitle: "Story" });

    await user.click(screen.getByRole("button", { name: /pause & exit/i }));

    expect(screen.getByText("story select")).toBeInTheDocument();
  });
});
