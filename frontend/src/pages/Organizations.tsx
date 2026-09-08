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

export function Organizations() {
  const { data, error, loading, setData } = useFetch(() => get<any>("/organizations"));
  const { data: users } = useFetch(() => get<any>("/users"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState({ name: "", slug: "", owner_id: "" });
  const [quotas, setQuotas] = useState<any | null>(null);
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => void } | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await get<any>("/organizations"));
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const rows = data.data ?? [];
  const allUsers: any[] = users?.data ?? [];

  function openCreate() {
    setEditing(null);
    setForm({ name: "", slug: "", owner_id: "" });
    setDialogOpen(true);
  }
  function openEdit(org: any) {
    setEditing(org);
    setForm({ name: org.name ?? "", slug: org.slug ?? "", owner_id: org.owner_id ?? "" });
    setDialogOpen(true);
  }
  async function submit() {
    if (editing) {
      await mutation.run(
        () => patch(`/organizations/${editing.id}`, { name: form.name, slug: form.slug, owner_id: form.owner_id || null }),
        "Organization updated."
      );
    } else {
      await mutation.run(() => post("/organizations", form), "Organization created.");
    }
    setDialogOpen(false);
  }
  async function openQuotas(org: any) {
    setQuotas({ org, values: await get<any>(`/organizations/${org.id}/quotas`) });
  }
  async function saveQuotas() {
    if (!quotas) return;
    await mutation.run(
      () => patch(`/organizations/${quotas.org.id}/quotas`, quotas.values),
      "Quotas updated."
    );
    setQuotas(null);
  }

  const columns: GridColDef[] = [
    { field: "name", headerName: "Name", flex: 1 },
    { field: "slug", headerName: "Slug", flex: 1 },
    {
      field: "owner_id",
      headerName: "Owner",
      flex: 1,
      renderCell: (p) => allUsers.find((u) => u.id === p.value)?.email ?? p.value ?? "—",
    },
    {
      field: "user_count",
      headerName: "Users",
      width: 90,
      renderCell: (p) => p.value ?? 0,
    },
    {
      field: "suspended",
      headerName: "Status",
      width: 130,
      renderCell: (p) =>
        p.row.deleted_at ? (
          <Chip label="Archived" size="small" />
        ) : p.value ? (
          <Chip label="Suspended" color="warning" size="small" />
        ) : (
          <Chip label="Active" color="success" size="small" />
        ),
    },
    { field: "created_at", headerName: "Created", flex: 1 },
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
          <Button size="small" onClick={() => openQuotas(p.row)}>
            Quotas
          </Button>
          {p.row.deleted_at ? (
            <Button
              size="small"
              color="success"
              onClick={() =>
                mutation.run(() => post(`/organizations/${p.row.id}/restore`), "Restored.")
              }
            >
              Restore
            </Button>
          ) : (
            <Button
              size="small"
              color="warning"
              onClick={() =>
                setConfirm({
                  title: "Archive organization",
                  message: `Archive ${p.row.name}? Users keep their records but the org is suspended.`,
                  action: () =>
                    mutation.run(() => del(`/organizations/${p.row.id}`), "Archived."),
                })
              }
            >
              Archive
            </Button>
          )}
        </Box>
      ),
    },
  ];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Organizations</Typography>
        <Button variant="contained" onClick={openCreate}>
          Create organization
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      {rows.length === 0 ? (
        <EmptyState message="No organizations yet." />
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
        title={editing ? "Edit organization" : "Create organization"}
        onClose={() => setDialogOpen(false)}
        onSubmit={submit}
        submitLabel={editing ? "Save" : "Create"}
      >
        <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <Field label="Slug" value={form.slug} onChange={(v) => setForm({ ...form, slug: v })} />
        <TextField
          select
          label="Owner"
          value={form.owner_id}
          onChange={(e) => setForm({ ...form, owner_id: e.target.value })}
          size="small"
          fullWidth
        >
          <MenuItem value="">— none —</MenuItem>
          {allUsers.map((u: any) => (
            <MenuItem key={u.id} value={u.id}>
              {u.email}
            </MenuItem>
          ))}
        </TextField>
      </FormDialog>
      <FormDialog
        open={quotas !== null}
        title={`Quotas — ${quotas?.org.name ?? ""}`}
        onClose={() => setQuotas(null)}
        onSubmit={saveQuotas}
      >
        {["storage_mb", "dataset_limit", "ai_requests_per_day", "api_requests_per_minute"].map((k) => (
          <Field
            key={k}
            label={k}
            type="number"
            value={String(quotas?.values?.[k] ?? "")}
            onChange={(v) => setQuotas({ ...quotas, values: { ...quotas.values, [k]: Number(v) } })}
          />
        ))}
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
