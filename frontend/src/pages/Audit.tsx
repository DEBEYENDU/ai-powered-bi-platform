import { useState } from "react";
import { Box, Button, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { download, get } from "../api";
import { EmptyState, ErrorBanner, Loading, useFetch } from "../components";

export function Audit() {
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [query, setQuery] = useState({ action: "", actor_id: "" });
  const { data, error, loading } = useFetch(
    () =>
      get<any>(
        `/audit?limit=500&${new URLSearchParams({
          ...(query.action ? { action: query.action } : {}),
          ...(query.actor_id ? { actor_id: query.actor_id } : {}),
        }).toString()}`
      ),
    [query]
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  let rows: any[] = data.data ?? [];
  if (from) rows = rows.filter((e) => (e.created_at ?? "") >= from);
  if (to) rows = rows.filter((e) => (e.created_at ?? "") <= to + "T23:59:59");

  const columns: GridColDef[] = [
    { field: "created_at", headerName: "Time", flex: 1.2 },
    { field: "action", headerName: "Action", flex: 1 },
    { field: "actor_id", headerName: "Actor", flex: 1 },
    { field: "resource_type", headerName: "Resource", flex: 0.8 },
    { field: "resource_id", headerName: "Resource ID", flex: 1 },
  ];

  const qs = (extra: Record<string, string>) =>
    new URLSearchParams({
      ...(query.action ? { action: query.action } : {}),
      ...(query.actor_id ? { actor_id: query.actor_id } : {}),
      ...extra,
    }).toString();

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Audit Log</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button variant="outlined" onClick={() => download(`/audit/export?format=csv&${qs({})}`, "audit.csv")}>
            Export CSV
          </Button>
          <Button variant="outlined" onClick={() => download(`/audit/export?format=json&${qs({})}`, "audit.json")}>
            Export JSON
          </Button>
        </Box>
      </Box>
      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <TextField label="Action filter" value={action} onChange={(e) => setAction(e.target.value)} size="small" />
        <TextField label="Actor filter" value={actor} onChange={(e) => setActor(e.target.value)} size="small" />
        <TextField label="From date" type="date" value={from} onChange={(e) => setFrom(e.target.value)} size="small" slotProps={{ inputLabel: { shrink: true } }} />
        <TextField label="To date" type="date" value={to} onChange={(e) => setTo(e.target.value)} size="small" slotProps={{ inputLabel: { shrink: true } }} />
        <Button variant="contained" onClick={() => setQuery({ action, actor_id: actor })}>
          Search
        </Button>
      </Box>
      {rows.length === 0 ? (
        <EmptyState message="No audit entries match." />
      ) : (
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(r) => r.id}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
          pageSizeOptions={[25, 50, 100]}
          autoHeight
        />
      )}
    </>
  );
}
