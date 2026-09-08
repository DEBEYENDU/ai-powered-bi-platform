import { useState } from "react";
import { Box, Button, Chip, TextField, Typography } from "@mui/material";
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

export function Flags() {
  const { data, error, loading, setData } = useFetch(() => get<any>("/flags"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState({ key: "", description: "", flag_type: "boolean", rules: "[]" });
  const [evalKey, setEvalKey] = useState("");
  const [evalResult, setEvalResult] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => void } | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await get<any>("/flags"));
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const rows: any[] = data.data ?? [];

  function openCreate() {
    setEditing(null);
    setForm({ key: "", description: "", flag_type: "boolean", rules: "[]" });
    setDialogOpen(true);
  }
  function openEdit(flag: any) {
    setEditing(flag);
    setForm({
      key: flag.key,
      description: flag.description ?? "",
      flag_type: flag.flag_type ?? "boolean",
      rules: JSON.stringify(flag.rules ?? [], null, 2),
    });
    setDialogOpen(true);
  }
  async function submit() {
    let rules: any[] = [];
    try {
      rules = JSON.parse(form.rules || "[]");
    } catch {
      setDialogOpen(false);
      return;
    }
    if (editing) {
      await mutation.run(
        () => patch(`/flags/${editing.key}`, { description: form.description, rules }),
        "Flag updated."
      );
    } else {
      await mutation.run(
        () => post("/flags", { key: form.key, description: form.description, flag_type: form.flag_type, rules }),
        "Flag created."
      );
    }
    setDialogOpen(false);
  }
  async function evaluate() {
    try {
      const result = await post<any>("/flags/evaluate", { key: evalKey });
      setEvalResult(`${result.key}: enabled=${result.enabled} (${result.reason})`);
    } catch (e) {
      setEvalResult(String(e));
    }
  }

  const columns: GridColDef[] = [
    { field: "key", headerName: "Key", flex: 1.2 },
    { field: "flag_type", headerName: "Type", width: 110 },
    { field: "version", headerName: "Ver", width: 70 },
    {
      field: "enabled",
      headerName: "State",
      width: 150,
      renderCell: (p) =>
        p.row.killed ? (
          <Chip label="Killed" color="error" size="small" />
        ) : p.value ? (
          <Chip label="On" color="success" size="small" />
        ) : (
          <Chip label="Off" size="small" />
        ),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 300,
      sortable: false,
      renderCell: (p) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          <Button size="small" onClick={() => openEdit(p.row)}>
            Edit
          </Button>
          <Button
            size="small"
            color="error"
            onClick={() =>
              setConfirm({
                title: "Kill switch",
                message: `Kill flag ${p.row.key}? It stays off until re-enabled.`,
                action: () => mutation.run(() => post(`/flags/${p.row.key}/kill`), "Killed."),
              })
            }
          >
            Kill
          </Button>
          <Button
            size="small"
            color="error"
            onClick={() =>
              setConfirm({
                title: "Delete flag",
                message: `Delete flag ${p.row.key}?`,
                action: () => mutation.run(() => del(`/flags/${p.row.key}`), "Deleted."),
              })
            }
          >
            Delete
          </Button>
        </Box>
      ),
    },
  ];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Feature Flags</Typography>
        <Button variant="contained" onClick={openCreate}>
          Create flag
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <TextField label="Evaluate flag key" value={evalKey} onChange={(e) => setEvalKey(e.target.value)} size="small" />
        <Button variant="outlined" onClick={evaluate}>
          Evaluate
        </Button>
        {evalResult && <Typography sx={{ alignSelf: "center" }}>{evalResult}</Typography>}
      </Box>
      {rows.length === 0 ? (
        <EmptyState message="No feature flags." />
      ) : (
        <DataGrid rows={rows} columns={columns} getRowId={(r) => r.key} autoHeight />
      )}
      <FormDialog
        open={dialogOpen}
        title={editing ? "Edit flag" : "Create flag"}
        onClose={() => setDialogOpen(false)}
        onSubmit={submit}
        submitLabel={editing ? "Save" : "Create"}
      >
        <Field label="Key" value={form.key} onChange={(v) => setForm({ ...form, key: v })} required />
        <Field label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
        <TextField
          label="Rules (JSON array)"
          value={form.rules}
          onChange={(e) => setForm({ ...form, rules: e.target.value })}
          multiline
          rows={5}
          fullWidth
          size="small"
          helperText='E.g. [{"name":"pct","percentage":50}]'
        />
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
