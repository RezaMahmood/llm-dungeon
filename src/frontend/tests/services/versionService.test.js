import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UNKNOWN_VERSION, getBackendVersion, getFrontendVersion } from "../../src/services/versionService.js";

vi.mock("axios", () => ({ default: { get: vi.fn() } }));

describe("versionService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("reads the frontend version from the build's stamped version.json", async () => {
    axios.get.mockResolvedValue({ data: { version: "1.4.0" } });

    await expect(getFrontendVersion()).resolves.toBe("1.4.0");
    expect(axios.get).toHaveBeenCalledWith("/version.json", { headers: { Accept: "application/json" } });
  });

  it("reads the backend version from the anonymous version endpoint", async () => {
    axios.get.mockResolvedValue({ data: { status: "success", version: "0.9.2" } });

    await expect(getBackendVersion()).resolves.toBe("0.9.2");
    // No Authorization header: this has to answer on the login screen too.
    expect(axios.get).toHaveBeenCalledWith("/api/version");
  });

  it("falls back to unknown when a fallback rewrite returns HTML instead of JSON", async () => {
    axios.get.mockResolvedValue({ data: "<!doctype html><html></html>" });

    await expect(getFrontendVersion()).resolves.toBe(UNKNOWN_VERSION);
  });

  it("falls back to unknown when the body carries no usable version", async () => {
    axios.get.mockResolvedValue({ data: { version: "  " } });

    await expect(getBackendVersion()).resolves.toBe(UNKNOWN_VERSION);
  });

  it("propagates a transport failure so the caller can report it per component", async () => {
    axios.get.mockRejectedValue(new Error("Network Error"));

    await expect(getBackendVersion()).rejects.toThrow("Network Error");
  });
});
