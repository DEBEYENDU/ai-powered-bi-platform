/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
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
import AddIcon from "@mui/icons-material/Add";
import RefreshIcon from "@mui/icons-material/Refresh";
import CancelIcon from "@mui/icons-material/Cancel";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TrainingRun {
  id: string;
  experiment_id: string;
  model_id: string;
  dataset_id: string;
  target_column: string;
  status: string;
  duration_seconds: number | null;
  metrics: Record<string, number>;
  parameters: Record<string, any>;
  created_at: string;
  logs: string | null;
}

interface ExperimentOption {
  id: string;
  name: string;
}

interface ModelOption {
  id: string;
  name: string;
}

interface DatasetOption {
  id: string;
  name: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const statusColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  pending: "default",
  running: "info",
  completed: "success",
  failed: "error",
  cancelled: "default",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsTraining() {
  const [runs, setRuns] = useState<TrainingRun[]>([]);
  const [experiments, setExperiments] = useState<ExperimentOption[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);
  const [selectedLogs, setSelectedLogs] = useState("");
  const [form, setForm] = useState({
    experiment_id: "",
    model_id: "",
    dataset_id: "",
    target_column: "",
    parameters: "{}",
  });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [runsRes, expRes, mdlRes, dsRes] = await Promise.allSettled([
        rget<{ training_runs: TrainingRun[] }>("/mlops/training"),
        rget<{ experiments: ExperimentOption[] }>("/mlops/experiments"),
        rget<{ models: ModelOption[] }>("/mlops/models"),
        rget<{ datasets: DatasetOption[] }>("/mlops/datasets"),
      ]);
      if (runsRes.status === "fulfilled") setRuns(runsRes.value.training_runs || []);
      if (expRes.status === "fulfilled") setExperiments(expRes.value.experiments || []);
      if (mdlRes.status === "fulfilled") setModels(mdlRes.value.models || []);
      if (dsRes.status === "fulfilled") setDatasets(dsRes.value.datasets || []);
    } catch (e: any) {
      setError(e.message || "Failed to load training data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleStartTraining = async () => {
    if (!form.experiment_id || !form.model_id || !form.dataset_id) return;
    setCreating(true);
    setError("");
    try {
      let params: Record<string, any> = {};
      try {
        params = JSON.parse(form.parameters || "{}");
      } catch {
        setError("Invalid parameters JSON");
        setCreating(false);
        return;
      }
      await rpost("/mlops/training", {
        experiment_id: form.experiment_id,
        model_id: form.model_id,
        dataset_id: form.dataset_id,
        target_column: form.target_column,
        parameters: params,
      });
      setDialogOpen(false);
      setForm({ experiment_id: "", model_id: "", dataset_id: "", target_column: "", parameters: "{}" });
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to start training");
    } finally {
      setCreating(false);
    }
  };

  const handleCancel = async (runId: string) => {
    try {
      await rpost(`/mlops/training/${runId}/cancel`, {});
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to cancel training run");
    }
  };

  const handleViewLogs = (logs: string) => {
    setSelectedLogs(logs || "No logs available.");
    setLogsDialogOpen(true);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Training Runs</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchAll} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Start Training
          </Button>
        </Box>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Launch and monitor model training runs
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : runs.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Run ID</TableCell>
                <TableCell>Experiment</TableCell>
                <TableCell>Model</TableCell>
                <TableCell>Dataset</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Duration</TableCell>
                <TableCell>Metrics</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {runs.map((r) => (
                <TableRow key={r.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: "monospace", fontWeight: 600 }}>
                      {r.id.slice(0, 8)}
                    </Typography>
                  </TableCell>
                  <TableCell>{r.experiment_id}</TableCell>
                  <TableCell>{r.model_id}</TableCell>
                  <TableCell>{r.dataset_id}</TableCell>
                  <TableCell>
                    <Chip label={r.status} size="small" color={statusColor[r.status] || "default"} />
                  </TableCell>
                  <TableCell align="right">
                    {r.duration_seconds != null ? (
                      <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                        {r.duration_seconds.toFixed(1)}s
                      </Typography>
                    ) : "-"}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {Object.entries(r.metrics || {}).slice(0, 2).map(([k, v]) => (
                        <Chip key={k} label={`${k}: ${typeof v === "number" ? v.toFixed(4) : v}`} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>{r.created_at ? new Date(r.created_at).toLocaleDateString() : "-"}</TableCell>
                  <TableCell align="center">
                    {r.status === "running" && (
                      <Tooltip title="Cancel">
                        <IconButton size="small" onClick={() => handleCancel(r.id)} color="error">
                          <CancelIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="View Logs">
                      <IconButton size="small" onClick={() => handleViewLogs(r.logs || "")}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Start Training Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Start Training</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <FormControl fullWidth required>
            <InputLabel>Experiment</InputLabel>
            <Select
              value={form.experiment_id}
              label="Experiment"
              onChange={(e) => setForm({ ...form, experiment_id: e.target.value })}
            >
              <MenuItem value=""><em>Select experiment</em></MenuItem>
              {experiments.map((exp) => (
                <MenuItem key={exp.id} value={exp.id}>{exp.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth required>
            <InputLabel>Model</InputLabel>
            <Select
              value={form.model_id}
              label="Model"
              onChange={(e) => setForm({ ...form, model_id: e.target.value })}
            >
              <MenuItem value=""><em>Select model</em></MenuItem>
              {models.map((m) => (
                <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth required>
            <InputLabel>Dataset</InputLabel>
            <Select
              value={form.dataset_id}
              label="Dataset"
              onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}
            >
              <MenuItem value=""><em>Select dataset</em></MenuItem>
              {datasets.map((d) => (
                <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Target Column"
            value={form.target_column}
            onChange={(e) => setForm({ ...form, target_column: e.target.value })}
            fullWidth
          />
          <TextField
            label="Parameters (JSON)"
            value={form.parameters}
            onChange={(e) => setForm({ ...form, parameters: e.target.value })}
            fullWidth
            multiline
            rows={4}
            placeholder='{"learning_rate": 0.01, "epochs": 100}'
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleStartTraining}
            disabled={!form.experiment_id || !form.model_id || !form.dataset_id || creating}
          >
            {creating ? <CircularProgress size={20} /> : "Start Training"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Logs Dialog */}
      <Dialog open={logsDialogOpen} onClose={() => setLogsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Training Logs</DialogTitle>
        <DialogContent>
          <Paper sx={{ p: 2, bgcolor: "grey.900", color: "grey.100", fontFamily: "monospace", fontSize: 12, whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>
            {selectedLogs}
          </Paper>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
