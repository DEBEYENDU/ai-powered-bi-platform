import { Card, CardContent, Grid, Typography } from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { get } from "../api";
import { EmptyState, ErrorBanner, Loading, useFetch } from "../components";

function StatCard({ title, value }: { title: string; value: React.ReactNode }) {
  return (
    <Card>
      <CardContent>
        <Typography color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Typography variant="h5">{value}</Typography>
      </CardContent>
    </Card>
  );
}

export function Overview() {
  const { data, error, loading } = useFetch(() => get<any>("/overview"));
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  const inv = data.inventory ?? {};
  const sys = data.system ?? {};
  const latencySeries = [
    { name: "avg", ms: sys.avg_response_time_ms ?? 0 },
    { name: "p95", ms: sys.api_latency_p95_ms ?? 0 },
  ];
  const resourceSeries = [
    { name: "CPU %", v: sys.cpu_percent ?? 0 },
    { name: "Memory %", v: sys.memory_percent ?? 0 },
    { name: "Disk %", v: sys.disk_percent ?? 0 },
  ];
  return (
    <>
      <Typography variant="h4" gutterBottom>
        Platform Overview
      </Typography>
      <Grid container spacing={2}>
        {[
          ["Health", data.health],
          ["Organizations", data.organizations],
          ["Users", data.users],
          ["Roles", data.roles ?? "—"],
          ["Firing alerts", data.firing_alerts],
          ["Feature flags", data.feature_flags],
          ["Dashboards", inv.dashboards ?? "—"],
          ["Datasets", inv.datasets ?? "—"],
          ["Reports", inv.reports ?? "—"],
          ["Throughput (rpm)", sys.api_throughput_rpm ?? 0],
          ["Cache hit rate", sys.cache_hit_rate ?? 0],
          ["Maintenance", data.maintenance?.mode ?? "off"],
        ].map(([title, value]) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={title as string}>
            <StatCard title={title as string} value={String(value)} />
          </Grid>
        ))}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Latency (ms)</Typography>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={latencySeries}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="ms" fill="#1e3a5f" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Resources (%)</Typography>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={resourceSeries}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Line dataKey="v" stroke="#0288d1" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      {data.inventory_source === "unavailable" && (
        <EmptyState message="Inventory counts unavailable — database unreachable." />
      )}
    </>
  );
}
