import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({
    instance: { logoutRedirect: vi.fn() },
    accounts: [{ name: "Ada B.", username: "ada@example.test" }],
  }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";

const renderAt = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthenticatedLayout>
        <p>screen content</p>
      </AuthenticatedLayout>
    </MemoryRouter>,
  );

describe("AuthenticatedLayout header selection (FR-001, FR-006, SC-002)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: true,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });
  });

  it.each(["/menu", "/admin", "/admin/accounts", "/admin/stories/new"])(
    "renders the nav bar (not the title bar) on %s",
    (path) => {
      renderAt(path);

      expect(screen.getByRole("navigation")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /pause & exit/i })).not.toBeInTheDocument();
    },
  );

  it("renders the title bar (not the nav bar) on the story-play screen", () => {
    renderAt("/game");

    expect(screen.getByRole("button", { name: /pause & exit/i })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("always renders its children below whichever header it chose", () => {
    for (const path of ["/menu", "/game"]) {
      const { unmount } = renderAt(path);
      expect(screen.getByText("screen content")).toBeInTheDocument();
      unmount();
    }
  });

  it("clamps the shell to the viewport on the story-play screen, so only its own scroll containers (e.g. .play-shell) can scroll", () => {
    // Regression for FR-001: a `minHeight`-only shell never constrains an unconstrained
    // descendant's height, so a tall transcript grew the whole page instead of scrolling
    // internally. `height: 100vh` (a ceiling) + `overflow: hidden` is what actually stops
    // that, and only story-play may impose it — every other screen needs the page free to
    // grow past the viewport (index.css's own comment on why it carries no blanket rule).
    const { container } = renderAt("/game");
    const shell = container.firstChild;

    // jsdom resolves the "100vh" the component sets to a pixel value against the test
    // window's height, so assert the *kind* of constraint (a `height`, not a `minHeight`)
    // rather than the literal string.
    expect(shell.style.height).not.toBe("");
    expect(shell.style.overflow).toBe("hidden");
    expect(shell.style.minHeight).toBe("");
  });

  it.each(["/menu", "/admin"])("leaves the shell free to grow past the viewport on %s", (path) => {
    const { container } = renderAt(path);
    const shell = container.firstChild;

    expect(shell.style.minHeight).not.toBe("");
    expect(shell.style.height).toBe("");
    expect(shell.style.overflow).toBe("");
  });
});
