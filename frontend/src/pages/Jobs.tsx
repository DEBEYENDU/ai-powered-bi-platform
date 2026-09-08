import { useState } from "react";
import { Box, Button, Card, CardContent, Grid, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { get, post } from "../api";
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

export function Jobs() {
  const { data, error, loading, setData } = useFetch(() => get<any>("/jobs"));
  const { data: queues } = useFetch(() => get<any>("/jobs/queues"));
  const [retryOpen, setRetryOpen] = useState(false);
  const [retryForm, setRetryForm] = useState({ task_id: "", task_name: "", args: "[]", kwargs: "{}" });
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await get<any>("/jobs"));
    }
  );

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;

  async function submitRetry() {
    let args: any[] = [];
    let kwargs: any = {};
    try {
      args = JSON.parse(retryForm.args || "[]");
      kwargs = JSON.parse(retryForm.kwargs || "{}");
    } catch {
      return;
    }
    await mutation.run(
      () =>
        post(`/jobs/${retryForm.task_id}/retry`, {
          task_name: retryForm.task_name,
          task_args: args,
          task_kwargs: kwargs,
        }),
      "Job re-queued."
    );
    setRetryOpen(false);
  }

  const detailRows: Array<[string, string]> = [
    ["Broker", data.broker ?? "unknown"],
    ["Running", String(data.running ?? 0)],
    ["Scheduled", String(data.scheduled ?? 0)],
    ["Reserved", String(data.reserved ?? 0)],
    ["Workers", (data.workers ?? []).join(", ") || "none"],
  ];
  if (data.detail) detailRows.push(["Detail", data.detail]);

  const queueColumns: GridColDef[] = [
    { field: "name", headerName: "Queue", flex: 1 },
    { field: "depth", headerName: "Depth", width: 110 },
    { field: "workers", headerName: "Workers", width: 110 },
  ];

  const liveTasks: any[] = [];
  const details: Record<string, Record<string, any[]>> = data.details ?? {};
  for (const group of Object.keys(details)) {
    const workers = details[group] ?? {};
    for (const worker of Object.keys(workers)) {
      for (const task of workers[worker] ?? []) {
        liveTasks.push({ id: task.id, name: task.name, worker, group });
      }
    }
  }
  const taskColumns: GridColDef[] = [
    { field: "id", headerName: "Task ID", flex: 1.4 },
    { field: "name", headerName: "Task", flex: 1 },
    { field: "worker", headerName: "Worker", flex: 0.8 },
    { field: "group", headerName: "State", width: 110 },
    {
      field: "actions",
      headerName: "Actions",
      width: 120,
      sortable: false,
      renderCell: (p) => (
        <Button
          size="small"
          color="error"
          onClick={() => mutation.run(() => post(`/jobs/${p.row.id}/cancel`), "Cancel requested.")}
        >
          Cancel
        </Button>
      ),
    },
  ];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Background Jobs</Typography>
        <Button variant="outlined" onClick={() => setRetryOpen(true)}>
          Retry job by ID
        </Button>
      </Box>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Worker status
              </Typography>
              {detailRows.map(([k, v]) => (
                <Typography key={k} variant="body2">
                  {k}: {v}
                </Typography>
              ))}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Queues
              </Typography>
              {(queues?.data ?? []).length === 0 ? (
                <EmptyState message="No queue data." />
              ) : (
                <DataGrid rows={queues.data} columns={queueColumns} getRowId={(r) => r.name} autoHeight hideFooter />
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
        Live tasks
      </Typography>
      {liveTasks.length === 0 ? (
        <EmptyState message="No running or scheduled tasks reported." />
      ) : (
        <DataGrid rows={liveTasks} columns={taskColumns} getRowId={(r) => r.id} autoHeight />
      )}
      <FormDialog open={retryOpen} title="Retry job" onClose={() => setRetryOpen(false)} onSubmit={submitRetry} submitLabel="Re-queue">
        <Field label="Task ID (original, for audit)" value={retryForm.task_id} onChange={(v) => setRetryForm({ ...retryForm, task_id: v })} required />
        <Field label="Task name (e.g. reports.generate)" value={retryForm.task_name} onChange={(v) => setRetryForm({ ...retryForm, task_name: v })} required />
        <Field label="Args (JSON array)" value={retryForm.args} onChange={(v) => setRetryForm({ ...retryForm, args: v })} />
        <Field label="Kwargs (JSON object)" value={retryForm.kwargs} onChange={(v) => setRetryForm({ ...retryForm, kwargs: v })} />
      </FormDialog>
    </>
  );
}
