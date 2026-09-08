import { useState } from "react";
import { Box, Button, Chip, MenuItem, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { rdel, rget, rpatch, rpost } from "../api";
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

const WIDGET_KINDS = ["kpi", "chart", "table", "text", "ai_insights", "forecast", "gauge"];

export function Dashboards() {
  const { data, error, loading, setData } = useFetch(() => rget<any>("/dashboards"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState({ name: "", description: "" });
  const [widgetsText, setWidgetsText] = useState("[]");
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => void } | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await rget<any>("/dashboards"));
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const rows: any[] = data.data ?? [];

  function openCreate() {
    setEditing(null);
    setForm({ name: "", description: "" });
    setWidgetsText("[]");
    setDialogOpen(true);
  }
  async function openEdit(d: any) {
    setEditing(d);
    const detail = await rget<any>(`/dashboards/${d.id}`);
    setForm({ name: detail.name ?? "", description: detail.description ?? "" });
    setWidgetsText(JSON.stringify(detail.widgets ?? [], null, 2));
    setDialogOpen(true);
  }
  async function submit() {
    let widgets: any[] = [];
    try {
      widgets = JSON.parse(widgetsText || "[]");
    } catch {
      return;
    }
    if (editing) {
      await mutation.run(
        () => rpatch(`/dashboards/${editing.id}`, { name: form.name, description: form.description, widgets }),
        "Dashboard updated."
      );
    } else {
      await mutation.run(
        () => rpost("/dashboards", { name: form.name, description: form.description, widgets }),
        "Dashboard created."
      );
    }
    setDialogOpen(false);
  }
  function addWidget() {
    try {
      const widgets = JSON.parse(widgetsText || "[]");
      widgets.push({
        widget_id: `w${widgets.length + 1}`,
        kind: "kpi",
        title: "New widget",
        config: {},
        order: widgets.length,
      });
      setWidgetsText(JSON.stringify(widgets, null, 2));
    } catch {
      /* fix JSON first */
    }
  }

  const columns: GridColDef[] = [
    { field: "name", headerName: "Name", flex: 1.2 },
    { field: "description", headerName: "Description", flex: 1.4 },
    { field: "widget_count", headerName: "Widgets", width: 100 },
    {
      field: "shared",
      headerName: "Shared",
      width: 110,
      renderCell: (p) => (p.value ? <Chip label="Shared" color="primary" size="small" /> : <Chip label="Private" size="small" />),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 340,
      sortable: false,
      renderCell: (p) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          <Button size="small" onClick={() => openEdit(p.row)}>
            Edit
          </Button>
          <Button
            size="small"
            onClick={() =>
              mutation.run(() => rpost(`/dashboards/${p.row.id}/share`, { shared: !p.row.shared }), "Sharing updated.")
            }
          >
            {p.row.shared ? "Unshare" : "Share"}
          </Button>
          <Button
            size="small"
            color="error"
            onClick={() =>
              setConfirm({
                title: "Delete dashboard",
                message: `Delete ${p.row.name}?`,
                action: () => mutation.run(() => rdel(`/dashboards/${p.row.id}`), "Deleted."),
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
        <Typography variant="h4">Dashboards</Typography>
        <Button variant="contained" onClick={openCreate}>
          Create dashboard
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      {rows.length === 0 ? (
        <EmptyState message="No dashboards yet." />
      ) : (
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(r) => r.id}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          pageSizeOptions={[10, 25, 50]}
          autoHeight
        />
      )}
      <FormDialog
        open={dialogOpen}
        title={editing ? "Edit dashboard" : "Create dashboard"}
        onClose={() => setDialogOpen(false)}
        onSubmit={submit}
        submitLabel={editing ? "Save" : "Create"}
      >
        <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <Field label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          <Typography variant="subtitle2">Widgets (JSON array)</Typography>
          <Button size="small" onClick={addWidget}>
            + Add widget
          </Button>
        </Box>
        <TextField
          value={widgetsText}
          onChange={(e) => setWidgetsText(e.target.value)}
          multiline
          rows={8}
          fullWidth
          size="small"
          helperText={`Kinds: ${WIDGET_KINDS.join(", ")}`}
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
