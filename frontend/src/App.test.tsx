import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

// The admin pages fetch on mount; stub the network so the test is hermetic.
vi.mock("./api", () => ({
  TOKEN_KEY: "bi_token",
  REFRESH_KEY: "bi_refresh_token",
  get: () => new Promise(() => {}),
  post: () => new Promise(() => {}),
  patch: () => new Promise(() => {}),
  del: () => new Promise(() => {}),
}));

describe("Admin dashboard", () => {
  beforeEach(() => {
    localStorage.setItem("bi_token", "test-token");
  });

  it("renders the navigation when authenticated", () => {
    render(<App />);
    for (const item of ["Users", "Organizations", "Health", "Audit", "Alerts", "Settings"]) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });
});
