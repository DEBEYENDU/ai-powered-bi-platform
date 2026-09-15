import { useState } from "react";
import { Box, Button, Card, CardContent, Chip, Grid, Typography } from "@mui/material";
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
import { ErrorBanner, Loading, useFetch } from "../components";

function MetricCard({
  title,
  value,
  unit,
  available,
}: {
  title: string;
  value: unknown;
  unit?: string;
  available?: boolean;
}) {
  const isUnavailable = available === false || value === null || value === undefined;
  const displayValue = isUnavailable ? "N/A" : String(value ?? 0);
  return (
    <Card>
      <CardContent>
        <Typography color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5 }}>
          <Typography variant="h5">{displayValue}</Typography>
          {unit && !isUnavailable && (
            <Typography variant="body2" color="text.secondary">
              {unit}
            </Typography>
          )}
        </Box>
        {isUnavailable && (
          <Chip label="Not configured" size="small" sx={{ mt: 0.5 }} />
        )}
      </CardContent>
    </Card>
  );
}

export function Metrics() {
  const [tick, setTick] = useState(0);
  const [auto, setAuto] = useState(true);
  const { data, error, loading } = useFetch(() => get<any>("/metrics"), [tick]);

  useFetch(async () => {
    if (!auto) return null;
    await new Promise((r) => setTimeout(r, 5000));
    setTick((t) => t + 1);
    return null;
  }, [tick, auto]);

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;

  const queueAvailable =
    data.job_queue_length !== "Not Configured" && data.job_queue_length !== null;
  const dbAvailable = data.db_connections !== null && data.db_connections !== undefined;
  const cacheAvailable =
    data.cache_hit_rate !== null && data.cache_hit_rate !== undefined;

  const cards: Array<{
    title: string;
    value: unknown;
    unit?: string;
    available?: boolean;
  }> = [
    { title: "Throughput", value: data.api_throughput_rpm, unit: "req/min" },
    { title: "Avg response", value: data.avg_response_time_ms, unit: "ms" },
    { title: "P95 latency", value: data.api_latency_p95_ms, unit: "ms" },
    { title: "Total requests", value: data.api_requests_total },
    { title: "Errors", value: data.api_errors_total },
    {
      title: "Cache hit rate",
      value: data.cache_hit_rate != null ? `${(data.cache_hit_rate * 100).toFixed(1)}%` : null,
      available: cacheAvailable,
    },
    {
      title: "Cache hits / misses",
      value:
        data.cache_hits != null || data.cache_misses != null
          ? `${data.cache_hits ?? 0} / ${data.cache_misses ?? 0}`
          : null,
      available: cacheAvailable,
    },
    {
      title: "DB connections",
      value: data.db_connections,
      unit: "checked out",
      available: dbAvailable,
    },
    {
      title: "Job queue",
      value: data.job_queue_length,
      available: queueAvailable,
    },
    { title: "Uptime", value: data.uptime_seconds, unit: "s" },
  ];
  const latencyData = [
    { name: "avg", ms: data.avg_response_time_ms ?? 0 },
    { name: "p95", ms: data.api_latency_p95_ms ?? 0 },
  ];
  const resourceData = [
    { name: "CPU %", v: data.cpu_percent ?? 0 },
    { name: "Memory %", v: data.memory_percent ?? 0 },
    { name: "Disk %", v: data.disk_percent ?? 0 },
  ];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">Metrics</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button variant={auto ? "contained" : "outlined"} onClick={() => setAuto(!auto)}>
            Auto-refresh {auto ? "on" : "off"}
          </Button>
          <Button
            variant="outlined"
            component="a"
            href="/api/v1/admin/metrics/prometheus"
            target="_blank"
          >
            Prometheus endpoint
          </Button>
        </Box>
      </Box>
      <Grid container spacing={2}>
        {cards.map(({ title, value, unit, available }) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={title}>
            <MetricCard title={title} value={value} unit={unit} available={available} />
          </Grid>
        ))}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Latency (ms)</Typography>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={latencyData}>
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
                <LineChart data={resourceData}>
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
    </>
  );
}
