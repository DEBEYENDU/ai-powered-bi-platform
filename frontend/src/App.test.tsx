import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

// The admin pages fetch on mount; stub the network so the test is hermetic.
vi.mock("./api", () => ({
  get: () => new Promise(() => {}),
  post: () => new Promise(() => {}),
  patch: () => new Promise(() => {}),
  del: () => new Promise(() => {}),
}));

describe("Admin dashboard", () => {
  it("renders the navigation", () => {
    render(<App />);
    for (const item of ["Users", "Organizations", "Health", "Audit", "Alerts", "Settings"]) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });
});
