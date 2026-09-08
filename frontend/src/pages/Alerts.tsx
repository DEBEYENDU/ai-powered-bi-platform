import { useState } from "react";
import { Box, Button, Chip, MenuItem, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { del, get, patch, post } from "../api";
import {
  ConfirmDialog,
  EmptyState,
  ErrorBanner,
  Field,
  FormDialog,
  Loading,
  NoticeBanner,
  useFetch,
  useMutation,
} from "../components";

export function Alerts() {
  const { data: rules, error: rulesError, loading: rulesLoading, setData: setRules } = useFetch(() =>
    get<any>("/alerts/rules")
  );
  const { data: incidents, error: incError } = useFetch(() => get<any>("/alerts/incidents"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: "", metric: "", operator: ">", threshold: "90", severity: "warning" });
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => void } | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setRules(await get<any>("/alerts/rules"));
    }
  );

  if (rulesLoading) return <Loading />;
  if (rulesError || !rules) return <ErrorBanner error={rulesError ?? "No data"} />;
  const ruleRows: any[] = rules.data ?? [];
  const incidentRows: any[] = incidents?.data ?? [];

  async function submit() {
    await mutation.run(
      () =>
        post("/alerts/rules", {
          name: form.name,
          metric: form.metric,
          operator: form.operator,
          threshold: Number(form.threshold),
          severity: form.severity,
        }),
      "Alert rule created."
    );
    setDialogOpen(false);
  }

  const ruleColumns: GridColDef[] = [
    { field: "name", headerName: "Name", flex: 1.2 },
    { field: "metric", headerName: "Metric", flex: 1 },
    { field: "operator", headerName: "Op", width: 70 },
    { field: "threshold", headerName: "Threshold", width: 110 },
    { field: "severity", headerName: "Severity", width: 110 },
    {
      field: "enabled",
      headerName: "Enabled",
      width: 110,
      renderCell: (p) => <Chip label={p.value ? "On" : "Off"} color={p.value ? "success" : "default"} size="small" />,
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 260,
      sortable: false,
      renderCell: (p) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          <Button
            size="small"
            onClick={() => mutation.run(() => patch(`/alerts/rules/${p.row.id}`, { enabled: !p.row.enabled }), "Updated.")}
          >
            {p.row.enabled ? "Disable" : "Enable"}
          </Button>
          <Button
            size="small"
            color="error"
            onClick={() =>
              setConfirm({
                title: "Delete rule",
                message: `Delete alert rule ${p.row.name}?`,
                action: () => mutation.run(() => del(`/alerts/rules/${p.row.id}`), "Deleted."),
              })
            }
          >
            Delete
          </Button>
        </Box>
      ),
    },
  ];

  const incidentColumns: GridColDef[] = [
    { field: "metric", headerName: "Metric", flex: 1 },
    { field: "observed_value", headerName: "Value", width: 110 },
    { field: "severity", headerName: "Severity", width: 110 },
    {
      field: "status",
      headerName: "Status",
      width: 130,
      renderCell: (p) => (
        <Chip
          label={p.value}
          size="small"
          color={p.value === "firing" ? "error" : p.value === "acknowledged" ? "warning" : "success"}
        />
      ),
    },
    { field: "created_at", headerName: "Fired at", flex: 1 },
    {
      field: "actions",
      headerName: "Actions",
      width: 140,
      sortable: false,
      renderCell: (p) =>
        p.row.status === "firing" ? (
          <Button size="small" onClick={() => mutation.run(() => post(`/alerts/incidents/${p.row.id}/ack`), "Acknowledged.")}>
            Acknowledge
          </Button>
        ) : null,
    },
  ];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Alerts</Typography>
        <Button variant="contained" onClick={() => setDialogOpen(true)}>
          Create rule
        </Button>
      </Box>
      <ErrorBanner error={mutation.error ?? incError} />
      <NoticeBanner notice={mutation.notice} />
      <Typography variant="h6" gutterBottom>
        Rules
      </Typography>
      {ruleRows.length === 0 ? (
        <EmptyState message="No alert rules." />
      ) : (
        <DataGrid rows={ruleRows} columns={ruleColumns} getRowId={(r) => r.id} autoHeight />
      )}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Incidents
      </Typography>
      {incidentRows.length === 0 ? (
        <EmptyState message="No incidents." />
      ) : (
        <DataGrid rows={incidentRows} columns={incidentColumns} getRowId={(r) => r.id} autoHeight />
      )}
      <FormDialog open={dialogOpen} title="Create alert rule" onClose={() => setDialogOpen(false)} onSubmit={submit} submitLabel="Create">
        <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <Field label="Metric (e.g. cpu_percent)" value={form.metric} onChange={(v) => setForm({ ...form, metric: v })} required />
        <TextField select label="Operator" value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })} size="small" fullWidth>
          {[">", "<", ">=", "<=", "==", "!="].map((op) => (
            <MenuItem key={op} value={op}>
              {op}
            </MenuItem>
          ))}
        </TextField>
        <Field label="Threshold" type="number" value={form.threshold} onChange={(v) => setForm({ ...form, threshold: v })} required />
        <TextField select label="Severity" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} size="small" fullWidth>
          {["info", "warning", "critical"].map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
      </FormDialog>
      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.title ?? ""}
        message={confirm?.message ?? ""}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          confirm?.action();
          setConfirm(null);
        }}
      />
    </>
  );
}
