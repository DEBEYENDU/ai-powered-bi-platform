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

const emptyForm = {
  email: "",
  password: "",
  full_name: "",
  username: "",
  organization_id: "",
};

export function Users() {
  const { data, error, loading, setData } = useFetch(() => get<any>("/users"));
  const { data: orgs } = useFetch(() => get<any>("/organizations"));
  const { data: roles } = useFetch(() => get<any>("/roles"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const [confirm, setConfirm] = useState<{ title: string; message: string; action: () => void } | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      const refreshed = await get<any>("/users");
      setData(refreshed);
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const rows = data.data ?? [];

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }
  async function openEdit(user: any) {
    setEditing(user);
    setForm({
      email: user.email ?? "",
      password: "",
      full_name: user.full_name ?? "",
      username: user.username ?? "",
      organization_id: user.organization_id ?? "",
    });
    try {
      const assigned = await get<any>(`/users/${user.id}/roles`);
      const allRoles: any[] = roles?.data ?? [];
      const ids = (assigned.data ?? [])
        .map((r: any) => allRoles.find((ar: any) => ar.name === r.name)?.id)
        .filter(Boolean);
      setRoleIds(ids.length ? ids : (assigned.data ?? []).map((r: any) => r.id));
    } catch {
      setRoleIds([]);
    }
    setDialogOpen(true);
  }
  async function submit() {
    if (editing) {
      const patchBody: any = {
        full_name: form.full_name,
        username: form.username,
        email: form.email,
        organization_id: form.organization_id,
      };
      await mutation.run(() => patch(`/users/${editing.id}`, patchBody), "User updated.");
    } else {
      await mutation.run(
        () =>
          post("/users", {
            email: form.email,
            password: form.password,
            full_name: form.full_name,
            username: form.username,
            organization_id: form.organization_id,
          }),
        "User created."
      );
    }
    setDialogOpen(false);
  }
  const ask = (title: string, message: string, action: () => void) =>
    setConfirm({ title, message, action });

  const columns: GridColDef[] = [
    { field: "full_name", headerName: "Name", flex: 1 },
    { field: "email", headerName: "Email", flex: 1.4 },
    { field: "username", headerName: "Username", flex: 1 },
    { field: "organization_id", headerName: "Organization", flex: 1 },
    {
      field: "roles",
      headerName: "Roles",
      flex: 1.2,
      renderCell: (p) => (p.value ?? []).join(", "),
    },
    {
      field: "is_active",
      headerName: "Status",
      width: 130,
      renderCell: (p) =>
        p.row.suspended ? (
          <Chip label="Suspended" color="warning" size="small" />
        ) : p.value ? (
          <Chip label="Active" color="success" size="small" />
        ) : (
          <Chip label="Inactive" size="small" />
        ),
    },
    { field: "last_login_at", headerName: "Last login", flex: 1 },
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
          {p.row.suspended ? (
            <Button size="small" onClick={() => mutation.run(() => post(`/users/${p.row.id}/unsuspend`), "Unsuspended.")}>
              Unsuspend
            </Button>
          ) : (
            <Button
              size="small"
              color="warning"
              onClick={() =>
                ask("Suspend user", `Suspend ${p.row.email}?`, () =>
                  mutation.run(() => post(`/users/${p.row.id}/suspend`), "Suspended.")
                )
              }
            >
              Suspend
            </Button>
          )}
          <Button
            size="small"
            color="error"
            onClick={() =>
              ask("Delete user", `Deactivate ${p.row.email}?`, () =>
                mutation.run(() => del(`/users/${p.row.id}`), "Deactivated.")
              )
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
        <Typography variant="h4">Users</Typography>
        <Button variant="contained" onClick={openCreate}>
          Create user
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      {rows.length === 0 ? (
        <EmptyState message="No users yet. Create the first one." />
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
        title={editing ? "Edit user" : "Create user"}
        onClose={() => setDialogOpen(false)}
        onSubmit={submit}
        submitLabel={editing ? "Save" : "Create"}
      >
        <Field label="Full name" value={form.full_name} onChange={(v) => setForm({ ...form, full_name: v })} />
        <Field label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} required />
        {!editing && (
          <Field
            label="Password"
            type="password"
            value={form.password}
            onChange={(v) => setForm({ ...form, password: v })}
            required
          />
        )}
        <Field label="Username" value={form.username} onChange={(v) => setForm({ ...form, username: v })} />
        <TextField
          select
          label="Organization"
          value={form.organization_id}
          onChange={(e) => setForm({ ...form, organization_id: e.target.value })}
          size="small"
          fullWidth
        >
          <MenuItem value="">— none —</MenuItem>
          {(orgs?.data ?? []).map((o: any) => (
            <MenuItem key={o.id} value={o.id}>
              {o.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField label="Available roles (assign after save)" value={(roles?.data ?? []).map((r: any) => r.name).join(", ")} size="small" fullWidth disabled helperText="Use Roles page or change-role to assign." />
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
