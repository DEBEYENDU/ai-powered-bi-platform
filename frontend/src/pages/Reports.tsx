import { useState } from "react";
import { Box, Button, Chip, MenuItem, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { download, rdel, rget, rpost } from "../api";
import {
  EmptyState,
  ErrorBanner,
  Field,
  FormDialog,
  Loading,
  NoticeBanner,
  useFetch,
  useMutation,
} from "../components";

const FORMATS = ["pdf", "docx", "xlsx", "csv", "json", "html", "pptx"];

export function Reports() {
  const { data, error, loading, setData } = useFetch(() => rget<any>("/reports"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ title: "", report_type: "custom", formats: ["pdf"] });
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await rget<any>("/reports"));
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const rows: any[] = data.data ?? [];

  async function submit() {
    await mutation.run(async () => {
      const created = await rpost<any>("/reports", {
        title: form.title,
        report_type: form.report_type,
        definition: { title: form.title, report_type: form.report_type, sections: [] },
      });
      await rpost("/reports/generate", {
        report_id: created.id,
        formats: form.formats,
        include_ai: false,
      });
    }, "Report created and generated.");
    setDialogOpen(false);
  }
  function toggleFormat(f: string) {
    setForm((s) => ({
      ...s,
      formats: s.formats.includes(f) ? s.formats.filter((x) => x !== f) : [...s.formats, f],
    }));
  }

  const columns: GridColDef[] = [
    { field: "title", headerName: "Title", flex: 1.2 },
    { field: "report_type", headerName: "Type", width: 130 },
    {
      field: "status",
      headerName: "Status",
      width: 130,
      renderCell: (p) => <Chip label={p.value} size="small" color={p.value === "published" ? "success" : "default"} />,
    },
    { field: "current_version", headerName: "Ver", width: 70 },
    {
      field: "actions",
      headerName: "Actions",
      width: 320,
      sortable: false,
      renderCell: (p) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          {FORMATS.slice(0, 3).map((f) => (
            <Button
              key={f}
              size="small"
              onClick={() => download(`/reports/${p.row.id}/download?format=${f}`, `report.${f}`, "/api/v1")}
            >
              {f.toUpperCase()}
            </Button>
          ))}
          <Button
            size="small"
            color="error"
            onClick={() => mutation.run(() => rdel(`/reports/${p.row.id}`), "Deleted.")}
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
        <Typography variant="h4">Reports</Typography>
        <Button variant="contained" onClick={() => setDialogOpen(true)}>
          Generate report
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      {rows.length === 0 ? (
        <EmptyState message="No reports yet." />
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
      <FormDialog open={dialogOpen} title="Generate report" onClose={() => setDialogOpen(false)} onSubmit={submit} submitLabel="Generate">
        <Field label="Title" value={form.title} onChange={(v) => setForm({ ...form, title: v })} required />
        <TextField
          select
          label="Type"
          value={form.report_type}
          onChange={(e) => setForm({ ...form, report_type: e.target.value })}
          size="small"
          fullWidth
        >
          {["custom", "executive", "sales", "financial", "inventory", "forecast", "performance"].map((t) => (
            <MenuItem key={t} value={t}>
              {t}
            </MenuItem>
          ))}
        </TextField>
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {FORMATS.map((f) => (
            <Chip
              key={f}
              label={f.toUpperCase()}
              color={form.formats.includes(f) ? "primary" : "default"}
              onClick={() => toggleFormat(f)}
            />
          ))}
        </Box>
      </FormDialog>
    </>
  );
}
