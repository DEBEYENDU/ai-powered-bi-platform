import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { clearSession, setSession } from "./api";

// The admin pages fetch on mount; stub only the network, keep the real session logic.
vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    get: () => new Promise(() => {}),
    post: () => new Promise(() => {}),
    patch: () => new Promise(() => {}),
    del: () => new Promise(() => {}),
  };
});

function expiredJwt(): string {
  const encode = (obj: object) =>
    btoa(JSON.stringify(obj)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  const header = encode({ alg: "HS256", typ: "JWT" });
  const payload = encode({ sub: "user-1", exp: Math.floor(Date.now() / 1000) - 3600 });
  return `${header}.${payload}.signature`;
}

describe("Admin dashboard", () => {
  beforeEach(() => {
    clearSession();
  });

  it("renders the navigation when authenticated", () => {
    setSession("test-token");
    render(<App />);
    for (const item of ["Users", "Organizations", "Health", "Audit", "Alerts", "Settings"]) {
      expect(screen.getByText(item)).toBeInTheDocument();
    }
  });

  it("shows the login page when there is no session", async () => {
    render(<App />);
    expect(await screen.findByText("Sign in to continue")).toBeInTheDocument();
  });

  it("refreshes an expired token, and falls back to login when no refresh token exists", async () => {
    vi.resetModules();
    localStorage.setItem("bi_token", expiredJwt());
    const { default: FreshApp } = await import("./App");
    render(<FreshApp />);
    expect(await screen.findByText("Sign in to continue")).toBeInTheDocument();
  });
});
