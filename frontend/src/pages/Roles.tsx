import { useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
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

export function Roles() {
  const { data, error, loading, setData } = useFetch(() => get<any>("/roles"));
  const { data: matrix } = useFetch(() => get<any>("/permissions/matrix"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState({ name: "", description: "" });
  const [grants, setGrants] = useState<string[]>([]);
  const [usersOf, setUsersOf] = useState<any | null>(null);
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => void } | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await get<any>("/roles"));
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const rows: any[] = data.data ?? data ?? [];
  const resources: Record<string, string[]> = matrix?.resources ?? {};

  function openCreate() {
    setEditing(null);
    setForm({ name: "", description: "" });
    setGrants([]);
    setDialogOpen(true);
  }
  async function openEdit(role: any) {
    setEditing(role);
    setForm({ name: role.name ?? "", description: role.description ?? "" });
    try {
      const detail = await get<any>(`/roles/${role.id}`);
      setGrants(detail.permission_codes ?? []);
    } catch {
      setGrants([]);
    }
    setDialogOpen(true);
  }
  async function submit() {
    if (editing) {
      await mutation.run(
        () => patch(`/roles/${editing.id}`, { name: form.name, description: form.description, permission_codes: grants }),
        "Role updated."
      );
    } else {
      await mutation.run(
        () => post("/roles", { name: form.name, description: form.description, permission_codes: grants }),
        "Role created."
      );
    }
    setDialogOpen(false);
  }
  function toggle(code: string) {
    setGrants((g) => (g.includes(code) ? g.filter((c) => c !== code) : [...g, code]));
  }
  async function openUsers(role: any) {
    setUsersOf({ role, users: await get<any>(`/roles/${role.id}/users`) });
  }

  const columns: GridColDef[] = [
    { field: "name", headerName: "Name", flex: 1 },
    { field: "description", headerName: "Description", flex: 1.4 },
    {
      field: "system_role",
      headerName: "Type",
      width: 130,
      renderCell: (p) =>
        p.value ? <Chip label="System" size="small" /> : <Chip label="Custom" color="primary" size="small" />,
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 340,
      sortable: false,
      renderCell: (p) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          <Button size="small" onClick={() => openUsers(p.row)}>
            Users
          </Button>
          {!p.row.system_role && (
            <>
              <Button size="small" onClick={() => openEdit(p.row)}>
                Edit
              </Button>
              <Button
                size="small"
                onClick={() =>
                  mutation.run(() => post(`/roles/${p.row.id}/clone`, { name: `${p.row.name} (copy)` }), "Cloned.")
                }
              >
                Clone
              </Button>
              <Button
                size="small"
                color="error"
                onClick={() =>
                  setConfirm({
                    title: "Delete role",
                    message: `Delete custom role ${p.row.name}?`,
                    action: () => mutation.run(() => del(`/roles/${p.row.id}`), "Deleted."),
                  })
                }
              >
                Delete
              </Button>
            </>
          )}
        </Box>
      ),
    },
  ];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Roles</Typography>
        <Button variant="contained" onClick={openCreate}>
          Create role
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      {rows.length === 0 ? (
        <EmptyState message="No roles." />
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
        title={editing ? "Edit role" : "Create role"}
        onClose={() => setDialogOpen(false)}
        onSubmit={submit}
        submitLabel={editing ? "Save" : "Create"}
      >
        <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <Field label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
        <Typography variant="subtitle2">
          {editing ? "Replace permission grants with selection below:" : "Permission grants:"}
        </Typography>
        <Box sx={{ maxHeight: 300, overflow: "auto", border: "1px solid #ddd", borderRadius: 1 }}>
          {Object.entries(resources).map(([resource, actions]) => (
            <Box key={resource} sx={{ p: 1 }}>
              <Typography variant="subtitle2" sx={{ textTransform: "capitalize" }}>
                {resource}
              </Typography>
              {actions.map((action) => {
                const code = `${resource}.${action}`;
                return (
                  <FormControlLabel
                    key={code}
                    control={<Checkbox size="small" checked={grants.includes(code)} onChange={() => toggle(code)} />}
                    label={action}
                  />
                );
              })}
            </Box>
          ))}
        </Box>
      </FormDialog>
      <FormDialog
        open={usersOf !== null}
        title={`Users with role ${usersOf?.role.name ?? ""}`}
        onClose={() => setUsersOf(null)}
        onSubmit={() => setUsersOf(null)}
        submitLabel="Close"
      >
        {(usersOf?.users?.data ?? []).length === 0 ? (
          <Typography color="text.secondary">No users assigned.</Typography>
        ) : (
          (usersOf?.users?.data ?? []).map((u: any) => (
            <Typography key={u.id}>
              {u.full_name || u.email} ({u.email})
            </Typography>
          ))
        )}
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
