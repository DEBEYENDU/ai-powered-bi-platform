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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Select,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AddIcon from "@mui/icons-material/Add";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useNavigate, useParams } from "react-router-dom";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ModelDetail {
  id: string;
  name: string;
  description: string;
  model_type: string;
  task_type: string;
  framework: string;
  status: string;
  owner: string;
  created_at: string;
  updated_at: string;
}

interface ModelVersion {
  id: string;
  model_id: string;
  version: string;
  status: string;
  metrics: Record<string, number>;
  description: string;
  created_at: string;
}

interface TrainingRun {
  id: string;
  experiment_id: string;
  status: string;
  duration_seconds: number | null;
  metrics: Record<string, number>;
  created_at: string;
}

interface Evaluation {
  id: string;
  version_id: string;
  metric_name: string;
  metric_value: number;
  dataset: string;
  created_at: string;
}

interface Deployment {
  id: string;
  model_version_id: string;
  environment: string;
  status: string;
  health: string;
  deployed_at: string;
}

interface MonitoringEntry {
  id: string;
  timestamp: string;
  predictions_count: number;
  avg_latency_ms: number;
  error_rate: number;
  drift_score: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const statusColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  registered: "default",
  training: "info",
  trained: "info",
  staging: "warning",
  production: "success",
  archived: "default",
  active: "success",
  stopped: "error",
  failed: "error",
  healthy: "success",
  degraded: "warning",
  unhealthy: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsModelDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [model, setModel] = useState<ModelDetail | null>(null);
  const [versions, setVersions] = useState<ModelVersion[]>([]);
  const [trainingRuns, setTrainingRuns] = useState<TrainingRun[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [monitoring, setMonitoring] = useState<MonitoringEntry[]>([]);

  const [versionDialogOpen, setVersionDialogOpen] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [versionForm, setVersionForm] = useState({ version: "", description: "" });

  const fetchAll = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const [mdl, ver, trn, evals, dep, mon] = await Promise.allSettled([
        rget<ModelDetail>(`/mlops/models/${id}`),
        rget<{ versions: ModelVersion[] }>(`/mlops/models/${id}/versions`),
        rget<{ training_runs: TrainingRun[] }>(`/mlops/models/${id}/training`),
        rget<{ evaluations: Evaluation[] }>(`/mlops/models/${id}/evaluations`),
        rget<{ deployments: Deployment[] }>(`/mlops/models/${id}/deployments`),
        rget<{ monitoring: MonitoringEntry[] }>(`/mlops/models/${id}/monitoring`),
      ]);
      if (mdl.status === "fulfilled") setModel(mdl.value);
      if (ver.status === "fulfilled") setVersions(ver.value.versions || []);
      if (trn.status === "fulfilled") setTrainingRuns(trn.value.training_runs || []);
      if (evals.status === "fulfilled") setEvaluations(evals.value.evaluations || []);
      if (dep.status === "fulfilled") setDeployments(dep.value.deployments || []);
      if (mon.status === "fulfilled") setMonitoring(mon.value.monitoring || []);
    } catch (e: any) {
      setError(e.message || "Failed to load model details");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleCreateVersion = async () => {
    if (!id || !versionForm.version.trim()) return;
    setCreatingVersion(true);
    setError("");
    try {
      await rpost(`/mlops/models/${id}/versions`, versionForm);
      setVersionDialogOpen(false);
      setVersionForm({ version: "", description: "" });
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to create version");
    } finally {
      setCreatingVersion(false);
    }
  };

  const handlePromote = async (versionId: string) => {
    try {
      await rpost(`/mlops/versions/${versionId}/promote`, { target_stage: "production" });
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to promote version");
    }
  };

  const handleArchive = async (versionId: string) => {
    try {
      await rpost(`/mlops/versions/${versionId}/archive`, {});
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to archive version");
    }
  };

  const handleRollback = async (versionId: string) => {
    try {
      await rpost(`/mlops/versions/${versionId}/rollback`, {});
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to rollback version");
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <IconButton onClick={() => navigate("/mlops/models")}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4">{model?.name || "Model Detail"}</Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchAll} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setVersionDialogOpen(true)}>
            Create Version
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : (
        <>
          {/* Model Info */}
          {model && (
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>Model Info</Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="body2" color="text.secondary">Description</Typography>
                  <Typography variant="body1">{model.description || "No description"}</Typography>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="body2" color="text.secondary">Type</Typography>
                  <Chip label={model.model_type} size="small" variant="outlined" />
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="body2" color="text.secondary">Framework</Typography>
                  <Typography variant="body2">{model.framework || "-"}</Typography>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="body2" color="text.secondary">Status</Typography>
                  <Chip label={model.status} size="small" color={statusColor[model.status] || "default"} />
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="body2" color="text.secondary">Owner</Typography>
                  <Typography variant="body2">{model.owner || "-"}</Typography>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="body2" color="text.secondary">Created</Typography>
                  <Typography variant="body2">{model.created_at ? new Date(model.created_at).toLocaleDateString() : "-"}</Typography>
                </Grid>
              </Grid>
            </Paper>
          )}

          {/* Versions */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Versions ({versions.length})</Typography>
            {versions.length === 0 ? (
              <Typography color="text.secondary">No data available yet.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Version</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell align="center">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {versions.map((v) => (
                      <TableRow key={v.id} hover>
                        <TableCell><Typography variant="body2" sx={{ fontFamily: "monospace", fontWeight: 600 }}>{v.version}</Typography></TableCell>
                        <TableCell><Chip label={v.status} size="small" color={statusColor[v.status] || "default"} /></TableCell>
                        <TableCell>{v.description || "-"}</TableCell>
                        <TableCell>{v.created_at ? new Date(v.created_at).toLocaleDateString() : "-"}</TableCell>
                        <TableCell align="center">
                          <Tooltip title="Promote to production">
                            <Button size="small" onClick={() => handlePromote(v.id)}>Promote</Button>
                          </Tooltip>
                          <Tooltip title="Archive this version">
                            <Button size="small" onClick={() => handleArchive(v.id)}>Archive</Button>
                          </Tooltip>
                          <Tooltip title="Rollback to this version">
                            <Button size="small" color="warning" onClick={() => handleRollback(v.id)}>Rollback</Button>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          {/* Training Runs */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Training Runs ({trainingRuns.length})</Typography>
            {trainingRuns.length === 0 ? (
              <Typography color="text.secondary">No data available yet.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Run ID</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Metrics</TableCell>
                      <TableCell>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {trainingRuns.map((r) => (
                      <TableRow key={r.id} hover>
                        <TableCell><Typography variant="body2" sx={{ fontFamily: "monospace", fontWeight: 600 }}>{r.id.slice(0, 8)}</Typography></TableCell>
                        <TableCell><Chip label={r.status} size="small" color={statusColor[r.status] || "default"} /></TableCell>
                        <TableCell>{r.duration_seconds != null ? `${r.duration_seconds.toFixed(1)}s` : "-"}</TableCell>
                        <TableCell>
                          <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                            {Object.entries(r.metrics || {}).slice(0, 3).map(([k, v]) => (
                              <Chip key={k} label={`${k}: ${typeof v === "number" ? v.toFixed(4) : v}`} size="small" variant="outlined" />
                            ))}
                          </Box>
                        </TableCell>
                        <TableCell>{r.created_at ? new Date(r.created_at).toLocaleDateString() : "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          {/* Evaluations */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Evaluations ({evaluations.length})</Typography>
            {evaluations.length === 0 ? (
              <Typography color="text.secondary">No data available yet.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      <TableCell>Value</TableCell>
                      <TableCell>Dataset</TableCell>
                      <TableCell>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {evaluations.map((e) => (
                      <TableRow key={e.id} hover>
                        <TableCell><Typography variant="body2" sx={{ fontWeight: 600 }}>{e.metric_name}</Typography></TableCell>
                        <TableCell><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{e.metric_value.toFixed(4)}</Typography></TableCell>
                        <TableCell>{e.dataset || "-"}</TableCell>
                        <TableCell>{e.created_at ? new Date(e.created_at).toLocaleDateString() : "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          {/* Deployments */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Deployments ({deployments.length})</Typography>
            {deployments.length === 0 ? (
              <Typography color="text.secondary">No data available yet.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Environment</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Health</TableCell>
                      <TableCell>Deployed At</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {deployments.map((d) => (
                      <TableRow key={d.id} hover>
                        <TableCell><Chip label={d.environment} size="small" variant="outlined" /></TableCell>
                        <TableCell><Chip label={d.status} size="small" color={statusColor[d.status] || "default"} /></TableCell>
                        <TableCell><Chip label={d.health} size="small" color={statusColor[d.health] || "default"} /></TableCell>
                        <TableCell>{d.deployed_at ? new Date(d.deployed_at).toLocaleString() : "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          {/* Monitoring */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Monitoring ({monitoring.length})</Typography>
            {monitoring.length === 0 ? (
              <Typography color="text.secondary">No data available yet.</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Timestamp</TableCell>
                      <TableCell align="right">Predictions</TableCell>
                      <TableCell align="right">Avg Latency</TableCell>
                      <TableCell align="right">Error Rate</TableCell>
                      <TableCell align="right">Drift Score</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {monitoring.map((m) => (
                      <TableRow key={m.id} hover>
                        <TableCell>{new Date(m.timestamp).toLocaleString()}</TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.predictions_count}</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.avg_latency_ms.toFixed(1)}ms</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{(m.error_rate * 100).toFixed(2)}%</Typography></TableCell>
                        <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{m.drift_score.toFixed(4)}</Typography></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </>
      )}

      {/* Create Version Dialog */}
      <Dialog open={versionDialogOpen} onClose={() => setVersionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Version</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <TextField
            label="Version"
            value={versionForm.version}
            onChange={(e) => setVersionForm({ ...versionForm, version: e.target.value })}
            fullWidth
            required
            placeholder="e.g. 1.0.0"
          />
          <TextField
            label="Description"
            value={versionForm.description}
            onChange={(e) => setVersionForm({ ...versionForm, description: e.target.value })}
            fullWidth
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVersionDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateVersion} disabled={!versionForm.version.trim() || creatingVersion}>
            {creatingVersion ? <CircularProgress size={20} /> : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
