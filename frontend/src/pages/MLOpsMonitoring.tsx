/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import { rget } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface MonitoringSummary {
  total_predictions: number;
  avg_latency_ms: number;
  error_rate: number;
  drift_score: number;
}

interface MetricEntry {
  id: string;
  model_id: string;
  timestamp: string;
  predictions_count: number;
  avg_latency_ms: number;
  error_rate: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
}

interface AlertEntry {
  id: string;
  model_id: string;
  severity: string;
  message: string;
  metric_name: string;
  observed_value: number;
  threshold: number;
  status: string;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function DriftIndicator({ score }: { score: number }) {
  if (score < 0.05) return <Chip icon={<CheckCircleIcon />} label="Normal" size="small" color="success" />;
  if (score < 0.15) return <Chip icon={<WarningAmberIcon />} label="Warning" size="small" color="warning" />;
  return <Chip icon={<ErrorIcon />} label="Critical" size="small" color="error" />;
}

const severityColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  info: "info",
  warning: "warning",
  critical: "error",
};

const alertStatusColor: Record<string, "default" | "success" | "warning" | "error"> = {
  firing: "error",
  acknowledged: "warning",
  resolved: "success",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsMonitoring() {
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [metrics, setMetrics] = useState<MetricEntry[]>([]);
  const [alerts, setAlerts] = useState<AlertEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [sumRes, metRes, alrRes] = await Promise.allSettled([
        rget<MonitoringSummary>("/mlops/monitoring/summary"),
        rget<{ metrics: MetricEntry[] }>("/mlops/monitoring/metrics"),
        rget<{ alerts: AlertEntry[] }>("/mlops/monitoring/alerts"),
      ]);
      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
      if (metRes.status === "fulfilled") setMetrics(metRes.value.metrics || []);
      if (alrRes.status === "fulfilled") setAlerts(alrRes.value.alerts || []);
    } catch (e: any) {
      setError(e.message || "Failed to load monitoring data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Monitoring</Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchAll} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Monitor model performance, latency, errors, and drift
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : (
        <>
          {/* Summary Cards */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Total Predictions</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>
                    {summary?.total_predictions ?? 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Avg Latency</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>
                    {summary?.avg_latency_ms?.toFixed(1) ?? "0"}ms
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Error Rate</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace", color: (summary?.error_rate ?? 0) > 0.05 ? "error.main" : "success.main" }}>
                    {((summary?.error_rate ?? 0) * 100).toFixed(2)}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Drift Score</Typography>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
                    <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>
                      {summary?.drift_score?.toFixed(4) ?? "0"}
                    </Typography>
                    {summary?.drift_score != null && <DriftIndicator score={summary.drift_score} />}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Recent Metrics */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Recent Metrics</Typography>
            {metrics.length === 0 ? (
              <Typography color="text.secondary">No data available yet.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Model</TableCell>
                      <TableCell>Timestamp</TableCell>
                      <TableCell align="right">Predictions</TableCell>
                      <TableCell align="right">Avg Latency</TableCell>
                      <TableCell align="right">P95 Latency</TableCell>
                      <TableCell align="right">P99 Latency</TableCell>
                      <TableCell align="right">Error Rate</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metrics.map((m) => (
                      <TableRow key={m.id} hover>
                        <TableCell><Typography variant="body2" sx={{ fontWeight: 600 }}>{m.model_id}</Typography></TableCell>
                        <TableCell>{new Date(m.timestamp).toLocaleString()}</TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.predictions_count}</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.avg_latency_ms.toFixed(1)}ms</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.p95_latency_ms.toFixed(1)}ms</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.p99_latency_ms.toFixed(1)}ms</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace", color: m.error_rate > 0.05 ? "error.main" : "inherit" }}>{(m.error_rate * 100).toFixed(2)}%</Typography></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          {/* Alerts */}
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Alerts</Typography>
            {alerts.length === 0 ? (
              <Typography color="text.secondary">No alerts.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Model</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Message</TableCell>
                      <TableCell>Metric</TableCell>
                      <TableCell align="right">Observed</TableCell>
                      <TableCell align="right">Threshold</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {alerts.map((a) => (
                      <TableRow key={a.id} hover>
                        <TableCell><Typography variant="body2" sx={{ fontWeight: 600 }}>{a.model_id}</Typography></TableCell>
                        <TableCell><Chip label={a.severity} size="small" color={severityColor[a.severity] || "default"} /></TableCell>
                        <TableCell><Typography variant="body2">{a.message}</Typography></TableCell>
                        <TableCell>{a.metric_name}</TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{a.observed_value}</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{a.threshold}</Typography></TableCell>
                        <TableCell><Chip label={a.status} size="small" color={alertStatusColor[a.status] || "default"} /></TableCell>
                        <TableCell>{a.created_at ? new Date(a.created_at).toLocaleString() : "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </>
      )}
    </Box>
  );
}
