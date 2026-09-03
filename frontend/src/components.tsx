import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

const NAV = [
  ["Overview", "/"],
  ["Users", "/users"],
  ["Organizations", "/orgs"],
  ["Roles", "/roles"],
  ["Health", "/health"],
  ["Metrics", "/metrics"],
  ["Audit", "/audit"],
  ["Alerts", "/alerts"],
  ["Jobs", "/jobs"],
  ["Flags", "/flags"],
  ["Settings", "/settings"],
];

export function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "Inter, system-ui, sans-serif" }}>
      <nav style={{ width: 220, background: "#1e3a5f", color: "#fff", padding: 16 }}>
        <h2 style={{ fontSize: 16 }}>BI Platform Admin</h2>
        {NAV.map(([label, to]) => (
          <Link
            key={to + label}
            to={to}
            style={{
              display: "block",
              color: pathname === to ? "#ffd166" : "#fff",
              padding: "8px 4px",
              textDecoration: "none",
            }}
          >
            {label}
          </Link>
        ))}
      </nav>
      <main style={{ flex: 1, padding: 24, background: "#f5f7fa" }}>{children}</main>
    </div>
  );
}

export function useFetch<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fn()
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error, loading };
}

export function Status({ value }: { value: string }) {
  const color = value === "ok" ? "green" : value === "down" || value === "firing" ? "red" : "orange";
  return <span style={{ color, fontWeight: 700 }}>{value}</span>;
}

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ background: "#fff", borderRadius: 8, padding: 16, marginBottom: 16 }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </section>
  );
}
