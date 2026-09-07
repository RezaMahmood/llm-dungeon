import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VersionBadge from "../../src/components/Common/VersionBadge.jsx";
import { getBackendVersion, getFrontendVersion } from "../../src/services/versionService.js";

vi.mock("../../src/services/versionService.js", () => ({
  UNKNOWN_VERSION: "unknown",
  getFrontendVersion: vi.fn(),
  getBackendVersion: vi.fn(),
}));

const badge = () => screen.getByRole("button", { name: "Version information" });

describe("VersionBadge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getFrontendVersion.mockResolvedValue("1.4.0");
    getBackendVersion.mockResolvedValue("0.9.2");
  });

  it("shows only the icon until it is hovered, and fetches nothing up front", () => {
    render(<VersionBadge />);

    expect(badge()).toBeInTheDocument();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    expect(getFrontendVersion).not.toHaveBeenCalled();
    expect(getBackendVersion).not.toHaveBeenCalled();
  });

  it("reveals both deployed versions on hover", async () => {
    const user = userEvent.setup();
    render(<VersionBadge />);

    await user.hover(badge());

    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent("Frontend");
    expect(tooltip).toHaveTextContent("Backend");
    await waitFor(() => expect(tooltip).toHaveTextContent("1.4.0"));
    expect(tooltip).toHaveTextContent("0.9.2");
  });

  it("hides the versions again when the pointer leaves", async () => {
    const user = userEvent.setup();
    render(<VersionBadge />);

    await user.hover(badge());
    await screen.findByRole("tooltip");
    await user.unhover(badge());

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("reveals the versions on keyboard focus too", async () => {
    const user = userEvent.setup();
    render(<VersionBadge />);

    await user.tab();

    expect(badge()).toHaveFocus();
    await waitFor(() => expect(screen.getByRole("tooltip")).toHaveTextContent("1.4.0"));
  });

  it("still reports the frontend version when the backend cannot be reached", async () => {
    // The two deploy independently — a backend mid-deploy must not blank out
    // the half that is answering.
    getBackendVersion.mockRejectedValue(new Error("Network Error"));
    const user = userEvent.setup();
    render(<VersionBadge />);

    await user.hover(badge());

    const tooltip = await screen.findByRole("tooltip");
    await waitFor(() => expect(tooltip).toHaveTextContent("1.4.0"));
    expect(tooltip).toHaveTextContent("unknown");
  });

  it("fetches the versions once, not on every hover", async () => {
    const user = userEvent.setup();
    render(<VersionBadge />);

    await user.hover(badge());
    await screen.findByRole("tooltip");
    await user.unhover(badge());
    await user.hover(badge());

    expect(getFrontendVersion).toHaveBeenCalledTimes(1);
    expect(getBackendVersion).toHaveBeenCalledTimes(1);
  });

  it("describes the icon with the tooltip only while it is open", async () => {
    const user = userEvent.setup();
    render(<VersionBadge />);

    expect(badge()).not.toHaveAttribute("aria-describedby");

    await user.hover(badge());

    const tooltip = await screen.findByRole("tooltip");
    expect(badge()).toHaveAttribute("aria-describedby", tooltip.id);
  });
});
