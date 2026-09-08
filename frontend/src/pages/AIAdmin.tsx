import { Card, CardContent, Grid, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { get } from "../api";
import { EmptyState, ErrorBanner, Loading, useFetch } from "../components";

export function AIAdmin() {
  const { data: overview, error: oErr, loading: oLoad } = useFetch(() => get<any>("/ai/overview"));
  const { data: prompts } = useFetch(() => get<any>("/ai/prompts"));
  const { data: vec } = useFetch(() => get<any>("/ai/vectorstore"));

  if (oLoad) return <Loading />;
  if (oErr || !overview) return <ErrorBanner error={oErr ?? "No data"} />;
  const mon: any = overview.monitoring ?? {};

  const cards: Array<[string, unknown]> = [
    ["Providers", (overview.providers ?? []).join(", ")],
    ["Models", (overview.models ?? []).join(", ")],
    ["Embedding model", overview.embedding_model],
    ["Registered tools", overview.tool_count],
    ["AI requests", mon.total_requests ?? "—"],
    ["Avg latency (ms)", mon.avg_latency_ms ?? "—"],
    ["Success rate", mon.success_rate ?? "—"],
    ["Total tokens", mon.total_tokens ?? "—"],
    ["Est. cost", mon.total_estimated_cost ?? "—"],
    ["Tool calls", mon.total_tool_calls ?? "—"],
    ["Failures", mon.total_failures ?? "—"],
    ["Vector backend", vec?.backend ?? "—"],
    ["Vector records", vec?.record_count ?? "—"],
  ];

  const promptColumns: GridColDef[] = [
    { field: "id", headerName: "Template", flex: 1 },
    { field: "preview", headerName: "Preview", flex: 2.4 },
  ];

  return (
    <>
      <Typography variant="h4" gutterBottom>
        AI Administration
      </Typography>
      <Grid container spacing={2}>
        {cards.map(([title, value]) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={title}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  {title}
                </Typography>
                <Typography variant="h6" sx={{ wordBreak: "break-word" }}>
                  {String(value)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Prompt templates
              </Typography>
              {(prompts?.data ?? []).length === 0 ? (
                <EmptyState message="No prompt templates." />
              ) : (
                <DataGrid
                  rows={prompts.data}
                  columns={promptColumns}
                  getRowId={(r) => r.id}
                  autoHeight
                  hideFooter
                />
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Retrieval stats
              </Typography>
              <pre>{JSON.stringify(overview.retrieval ?? {}, null, 2)}</pre>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
}
