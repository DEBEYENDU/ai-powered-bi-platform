import { useState } from "react";
import { Box, Button, Card, CardContent, Grid, Typography } from "@mui/material";
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

  const cards: Array<[string, unknown]> = [
    ["Throughput (req/min)", data.api_throughput_rpm],
    ["Avg response (ms)", data.avg_response_time_ms],
    ["P95 latency (ms)", data.api_latency_p95_ms],
    ["Total requests", data.api_requests_total],
    ["Errors", data.api_errors_total],
    ["Cache hit rate", data.cache_hit_rate],
    ["Cache hits / misses", `${data.cache_hits ?? 0} / ${data.cache_misses ?? 0}`],
    ["DB connections", data.db_connections],
    ["Queue length", data.job_queue_length],
    ["Uptime (s)", data.uptime_seconds],
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
        {cards.map(([title, value]) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={title}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  {title}
                </Typography>
                <Typography variant="h5">{String(value)}</Typography>
              </CardContent>
            </Card>
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
