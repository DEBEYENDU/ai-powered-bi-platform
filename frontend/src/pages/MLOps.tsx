/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
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
  Tabs,
  Tab,
  Tooltip,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useNavigate } from "react-router-dom";
import { rget } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ModelSummary {
  id: string;
  name: string;
  model_type: string;
  status: string;
  owner: string;
  created_at: string;
}

interface ExperimentSummary {
  id: string;
  name: string;
  objective: string;
  status: string;
  created_at: string;
}

interface TrainingRunSummary {
  id: string;
  experiment_id: string;
  model_id: string;
  status: string;
  duration_seconds: number | null;
  created_at: string;
}

interface DeploymentSummary {
  id: string;
  model_id: string;
  model_version_id: string;
  environment: string;
  status: string;
  health: string;
  deployed_at: string;
}

interface MonitoringSummary {
  total_predictions: number;
  avg_latency_ms: number;
  error_rate: number;
  drift_score: number;
}

interface DriftSummary {
  total_checks: number;
  normal: number;
  warning: number;
  critical: number;
}

interface OverviewData {
  total_models: number;
  total_versions: number;
  total_deployments: number;
  status_distribution: Record<string, number>;
}

/* ------------------------------------------------------------------ */
/*  Status color helper                                                */
/* ------------------------------------------------------------------ */

const statusColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  registered: "default",
  training: "info",
  trained: "info",
  validating: "warning",
  validated: "info",
  staging: "warning",
  production: "success",
  archived: "default",
  active: "success",
  stopped: "error",
  failed: "error",
  pending: "default",
  running: "info",
  completed: "success",
  cancelled: "default",
  healthy: "success",
  degraded: "warning",
  unhealthy: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOps() {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [trainingRuns, setTrainingRuns] = useState<TrainingRunSummary[]>([]);
  const [deployments, setDeployments] = useState<DeploymentSummary[]>([]);
  const [monitoring, setMonitoring] = useState<MonitoringSummary | null>(null);
  const [drift, setDrift] = useState<DriftSummary | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [ov, mdl, exp, trn, dep, mon, drf] = await Promise.allSettled([
        rget<OverviewData>("/mlops/overview"),
        rget<{ models: ModelSummary[] }>("/mlops/models"),
        rget<{ experiments: ExperimentSummary[] }>("/mlops/experiments"),
        rget<{ training_runs: TrainingRunSummary[] }>("/mlops/training"),
        rget<{ deployments: DeploymentSummary[] }>("/mlops/deployments"),
        rget<MonitoringSummary>("/mlops/monitoring/summary"),
        rget<DriftSummary>("/mlops/drift/summary"),
      ]);
      if (ov.status === "fulfilled") setOverview(ov.value);
      if (mdl.status === "fulfilled") setModels(mdl.value.models || []);
      if (exp.status === "fulfilled") setExperiments(exp.value.experiments || []);
      if (trn.status === "fulfilled") setTrainingRuns(trn.value.training_runs || []);
      if (dep.status === "fulfilled") setDeployments(dep.value.deployments || []);
      if (mon.status === "fulfilled") setMonitoring(mon.value);
      if (drf.status === "fulfilled") setDrift(drf.value);
    } catch (e: any) {
      setError(e.message || "Failed to load MLOps data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const tabLabels = ["Overview", "Models", "Experiments", "Training", "Deployments", "Monitoring", "Drift"];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">MLOps</Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchAll} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage models, experiments, training, deployments, and monitoring
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        {tabLabels.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      {loading && <CircularProgress />}

      {/* Overview Tab */}
      {!loading && tab === 0 && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Total Models</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_models ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Total Versions</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_versions ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Deployments</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_deployments ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Monitoring</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{monitoring?.total_predictions ?? 0} predictions</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {overview?.status_distribution && Object.keys(overview.status_distribution).length > 0 && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>Status Distribution</Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                {Object.entries(overview.status_distribution).map(([status, count]) => (
                  <Chip
                    key={status}
                    label={`${status}: ${count}`}
                    color={statusColor[status] || "default"}
                    variant="outlined"
                  />
                ))}
              </Box>
            </Paper>
          )}

          {!overview && <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>}
        </>
      )}

      {/* Models Tab */}
      {!loading && tab === 1 && (
        models.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Owner</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {models.map((m) => (
                  <TableRow key={m.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/mlops/models/${m.id}`)}>
                    <TableCell><Typography variant="body2" sx={{ fontWeight: 600 }}>{m.name}</Typography></TableCell>
                    <TableCell><Chip label={m.model_type} size="small" variant="outlined" /></TableCell>
                    <TableCell><Chip label={m.status} size="small" color={statusColor[m.status] || "default"} /></TableCell>
                    <TableCell>{m.owner || "-"}</TableCell>
                    <TableCell>{m.created_at ? new Date(m.created_at).toLocaleDateString() : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )
      )}

      {/* Experiments Tab */}
      {!loading && tab === 2 && (
        experiments.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Objective</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {experiments.map((e) => (
                  <TableRow key={e.id} hover>
                    <TableCell><Typography variant="body2" sx={{ fontWeight: 600 }}>{e.name}</Typography></TableCell>
                    <TableCell>{e.objective || "-"}</TableCell>
                    <TableCell><Chip label={e.status} size="small" color={statusColor[e.status] || "default"} /></TableCell>
                    <TableCell>{e.created_at ? new Date(e.created_at).toLocaleDateString() : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )
      )}

      {/* Training Tab */}
      {!loading && tab === 3 && (
        trainingRuns.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Run ID</TableCell>
                  <TableCell>Experiment</TableCell>
                  <TableCell>Model</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trainingRuns.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell><Typography variant="body2" sx={{ fontFamily: "monospace", fontWeight: 600 }}>{r.id.slice(0, 8)}</Typography></TableCell>
                    <TableCell>{r.experiment_id}</TableCell>
                    <TableCell>{r.model_id}</TableCell>
                    <TableCell><Chip label={r.status} size="small" color={statusColor[r.status] || "default"} /></TableCell>
                    <TableCell>{r.duration_seconds != null ? `${r.duration_seconds.toFixed(1)}s` : "-"}</TableCell>
                    <TableCell>{r.created_at ? new Date(r.created_at).toLocaleDateString() : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )
      )}

      {/* Deployments Tab */}
      {!loading && tab === 4 && (
        deployments.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Model</TableCell>
                  <TableCell>Version</TableCell>
                  <TableCell>Environment</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Health</TableCell>
                  <TableCell>Deployed At</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {deployments.map((d) => (
                  <TableRow key={d.id} hover>
                    <TableCell>{d.model_id}</TableCell>
                    <TableCell>{d.model_version_id}</TableCell>
                    <TableCell><Chip label={d.environment} size="small" variant="outlined" /></TableCell>
                    <TableCell><Chip label={d.status} size="small" color={statusColor[d.status] || "default"} /></TableCell>
                    <TableCell><Chip label={d.health} size="small" color={statusColor[d.health] || "default"} /></TableCell>
                    <TableCell>{d.deployed_at ? new Date(d.deployed_at).toLocaleString() : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )
      )}

      {/* Monitoring Tab */}
      {!loading && tab === 5 && (
        monitoring ? (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Total Predictions</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>{monitoring.total_predictions}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Avg Latency</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>{monitoring.avg_latency_ms.toFixed(1)}ms</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Error Rate</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>{(monitoring.error_rate * 100).toFixed(2)}%</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Drift Score</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, fontFamily: "monospace" }}>{monitoring.drift_score.toFixed(4)}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>
        )
      )}

      {/* Drift Tab */}
      {!loading && tab === 6 && (
        drift ? (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Total Checks</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{drift.total_checks}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Normal</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, color: "success.main" }}>{drift.normal}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Warning</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, color: "warning.main" }}>{drift.warning}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Critical</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, color: "error.main" }}>{drift.critical}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        ) : (
          <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>
        )
      )}
    </Box>
  );
}
