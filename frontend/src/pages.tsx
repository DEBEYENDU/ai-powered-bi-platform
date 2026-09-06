import { useState } from "react";
import { get, post } from "./api";
import { Card, Status, useFetch } from "./components";

export function Overview() {
  const { data, error, loading } = useFetch(() => get<any>("/overview"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Platform Overview</h1>
      <Card title="Health">
        <Status value={data.health} />
      </Card>
      <Card title="Counts">
        <p>Organizations: {data.organizations}</p>
        <p>Users: {data.users}</p>
        <p>Firing alerts: {data.firing_alerts}</p>
        <p>Feature flags: {data.feature_flags}</p>
      </Card>
      <Card title="Maintenance">
        <p>
          Mode: <Status value={data.maintenance.mode} /> {data.maintenance.message}
        </p>
      </Card>
    </>
  );
}

export function Users() {
  const { data, error, loading } = useFetch(() => get<any>("/users"));
  const [email, setEmail] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  async function createUser() {
    setCreateError(null);
    try {
      await post("/users", { email, password: "ChangeMe123!" });
      location.reload();
    } catch (e) {
      setCreateError(String(e));
    }
  }
  return (
    <>
      <h1>Users</h1>
      {createError && <p style={{ color: "red" }}>Failed to create user: {createError}</p>}
      <Card title="Create user">
        <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button onClick={createUser}>Create</button>
      </Card>
      <Card title={`All users (${data.data.length})`}>
        <table cellPadding={6}>
          <thead>
            <tr>
              <th>Email</th>
              <th>Active</th>
              <th>Suspended</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.data.map((u: any) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{String(u.is_active)}</td>
                <td>{String(u.suspended)}</td>
                <td>
                  <button onClick={() => post(`/users/${u.id}/suspend`).then(() => location.reload())}>
                    Suspend
                  </button>{" "}
                  <button onClick={() => post(`/users/${u.id}/unsuspend`).then(() => location.reload())}>
                    Unsuspend
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

export function Orgs() {
  const { data, error, loading } = useFetch(() => get<any>("/organizations"));
  const [name, setName] = useState("");
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Organizations</h1>
      <Card title="Create organization">
        <input placeholder="name" value={name} onChange={(e) => setName(e.target.value)} />
        <button onClick={() => post("/organizations", { name }).then(() => location.reload())}>
          Create
        </button>
      </Card>
      <Card title="All organizations">
        <ul>
          {data.data.map((o: any) => (
            <li key={o.id}>
              {o.name} ({o.slug}) {o.suspended ? "(suspended)" : ""}
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}

export function Roles() {
  const { data, error, loading } = useFetch(() => get<any>("/roles"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Roles & Permissions</h1>
      <Card title="Roles">
        <ul>
          {data.data.map((r: any) => (
            <li key={r.id}>
              {r.name} {r.system_role ? "(system)" : ""}
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}

export function Health() {
  const { data, error, loading } = useFetch(() => get<any>("/health"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>
        Health — <Status value={data.overall} />
      </h1>
      {data.services.map((s: any) => (
        <Card key={s.service} title={s.service}>
          <Status value={s.status} /> — {s.latency_ms}ms — {s.detail}
        </Card>
      ))}
    </>
  );
}

export function Metrics() {
  const { data, error, loading } = useFetch(() => get<any>("/metrics"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Metrics</h1>
      <Card title="System snapshot">
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </Card>
    </>
  );
}

export function Audit() {
  const { data, error, loading } = useFetch(() => get<any>("/audit?limit=100"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Audit Log</h1>
      <Card title={`${data.data.length} entries`}>
        <table cellPadding={6}>
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Resource</th>
            </tr>
          </thead>
          <tbody>
            {data.data.map((e: any) => (
              <tr key={e.id}>
                <td>{e.created_at}</td>
                <td>{e.action}</td>
                <td>{e.actor_id}</td>
                <td>
                  {e.resource_type}:{e.resource_id}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

export function Alerts() {
  const { data, error, loading } = useFetch(() => get<any>("/alerts/incidents"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Alert Incidents</h1>
      {data.data.map((i: any) => (
        <Card key={i.id} title={`${i.metric} = ${i.observed_value}`}>
          <Status value={i.status} /> — {i.severity}{" "}
          <button onClick={() => post(`/alerts/incidents/${i.id}/ack`).then(() => location.reload())}>
            Acknowledge
          </button>
        </Card>
      ))}
      {data.data.length === 0 && <p>No incidents.</p>}
    </>
  );
}

export function Jobs() {
  const { data, error, loading } = useFetch(() => get<any>("/jobs"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Background Jobs</h1>
      <Card title="Broker">
        <p>
          {data.broker} — workers: {(data.workers || []).join(", ") || "none"}
        </p>
        <p>
          Running: {data.running} · Scheduled: {data.scheduled} · Reserved: {data.reserved}
        </p>
      </Card>
    </>
  );
}

export function Flags() {
  const { data, error, loading } = useFetch(() => get<any>("/flags"));
  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  return (
    <>
      <h1>Feature Flags</h1>
      {data.data.map((f: any) => (
        <Card key={f.key} title={`${f.key} (v${f.version})`}>
          <p>
            Enabled: {String(f.enabled)} · Killed: {String(f.killed)}
          </p>
          <button onClick={() => post(`/flags/${f.key}/kill`).then(() => location.reload())}>
            Kill switch
          </button>
        </Card>
      ))}
    </>
  );
}

export function Settings() {
  const { data, error, loading } = useFetch(() => get<any>("/settings"));
  const {
    data: maint,
    error: maintError,
    loading: maintLoading,
  } = useFetch(() => get<any>("/maintenance"));
  const [mode, setMode] = useState("off");
  const [notice, setNotice] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  if (loading || maintLoading) return <p>Loading…</p>;
  if (error) return <p>Error: {error}</p>;
  if (maintError) return <p>Error: {maintError}</p>;
  const currentMode = maint.mode as string;
  async function applyMaintenance() {
    setApplyError(null);
    setNotice(null);
    if (mode !== "off" && mode !== currentMode) {
      const ok = window.confirm(
        `Switch maintenance mode from "${currentMode}" to "${mode}"? ` +
          (mode === "readonly"
            ? "Write endpoints will return 503 until you switch back."
            : "Almost everything will return 503 until you switch back.")
      );
      if (!ok) return;
    }
    try {
      const updated = await post<any>("/maintenance", { mode });
      setNotice(`Maintenance mode is now "${updated.mode}".`);
    } catch (e) {
      // Backend errors (e.g. 503 while locked out) are shown, never swallowed.
      setApplyError(String(e));
    }
  }
  return (
    <>
      <h1>Settings</h1>
      {notice && <p style={{ color: "green" }}>{notice}</p>}
      {applyError && <p style={{ color: "red" }}>Failed to apply: {applyError}</p>}
      <Card title="System settings">
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </Card>
      <Card title="Maintenance mode">
        <p>
          Current mode: <strong>{currentMode}</strong>
        </p>
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="off">off</option>
          <option value="readonly">readonly</option>
          <option value="maintenance">maintenance</option>
        </select>{" "}
        <button onClick={applyMaintenance}>Apply</button>
      </Card>
    </>
  );
}
