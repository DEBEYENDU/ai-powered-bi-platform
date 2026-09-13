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
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import UndoIcon from "@mui/icons-material/Undo";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Deployment {
  id: string;
  model_id: string;
  model_version_id: string;
  environment: string;
  status: string;
  health: string;
  traffic_percentage: number;
  deployed_at: string;
  updated_at: string;
}

interface ModelOption {
  id: string;
  name: string;
}

interface VersionOption {
  id: string;
  version: string;
  model_id: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const statusColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  pending: "default",
  active: "success",
  stopped: "error",
  failed: "error",
  rolling_back: "warning",
};

const healthColor: Record<string, "default" | "success" | "warning" | "error"> = {
  healthy: "success",
  degraded: "warning",
  unhealthy: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsDeployments() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [versions, setVersions] = useState<VersionOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    model_version_id: "",
    environment: "staging",
    traffic_percentage: "100",
  });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [depRes, mdlRes, verRes] = await Promise.allSettled([
        rget<{ deployments: Deployment[] }>("/mlops/deployments"),
        rget<{ models: ModelOption[] }>("/mlops/models"),
        rget<{ versions: VersionOption[] }>("/mlops/versions"),
      ]);
      if (depRes.status === "fulfilled") setDeployments(depRes.value.deployments || []);
      if (mdlRes.status === "fulfilled") setModels(mdlRes.value.models || []);
      if (verRes.status === "fulfilled") setVersions(verRes.value.versions || []);
    } catch (e: any) {
      setError(e.message || "Failed to load deployments");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleCreate = async () => {
    if (!form.model_version_id) return;
    setCreating(true);
    setError("");
    try {
      await rpost("/mlops/deployments", {
        model_version_id: form.model_version_id,
        environment: form.environment,
        traffic_percentage: parseInt(form.traffic_percentage),
      });
      setDialogOpen(false);
      setForm({ model_version_id: "", environment: "staging", traffic_percentage: "100" });
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to create deployment");
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (deploymentId: string) => {
    try {
      await rpost(`/mlops/deployments/${deploymentId}/activate`, {});
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to activate deployment");
    }
  };

  const handleStop = async (deploymentId: string) => {
    if (!confirm("Stop this deployment?")) return;
    try {
      await rpost(`/mlops/deployments/${deploymentId}/stop`, {});
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to stop deployment");
    }
  };

  const handleRollback = async (deploymentId: string) => {
    try {
      await rpost(`/mlops/deployments/${deploymentId}/rollback`, {});
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to rollback deployment");
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Deployments</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchAll} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Create Deployment
          </Button>
        </Box>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Deploy and manage model versions across environments
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : deployments.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
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
                <TableCell align="right">Traffic</TableCell>
                <TableCell>Deployed At</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {deployments.map((d) => (
                <TableRow key={d.id} hover>
                  <TableCell><Typography variant="body2" sx={{ fontWeight: 600 }}>{d.model_id}</Typography></TableCell>
                  <TableCell><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{d.model_version_id}</Typography></TableCell>
                  <TableCell><Chip label={d.environment} size="small" variant="outlined" /></TableCell>
                  <TableCell><Chip label={d.status} size="small" color={statusColor[d.status] || "default"} /></TableCell>
                  <TableCell><Chip label={d.health} size="small" color={healthColor[d.health] || "default"} /></TableCell>
                  <TableCell align="right"><Typography variant="body2" sx={{ fontFamily: "monospace" }}>{d.traffic_percentage}%</Typography></TableCell>
                  <TableCell>{d.deployed_at ? new Date(d.deployed_at).toLocaleString() : "-"}</TableCell>
                  <TableCell align="center">
                    {d.status !== "active" && (
                      <Tooltip title="Activate">
                        <IconButton size="small" onClick={() => handleActivate(d.id)} color="success">
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {d.status === "active" && (
                      <Tooltip title="Stop">
                        <IconButton size="small" onClick={() => handleStop(d.id)} color="error">
                          <StopIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Rollback">
                      <IconButton size="small" onClick={() => handleRollback(d.id)} color="warning">
                        <UndoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Deployment Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Deployment</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <FormControl fullWidth required>
            <InputLabel>Model Version</InputLabel>
            <Select
              value={form.model_version_id}
              label="Model Version"
              onChange={(e) => setForm({ ...form, model_version_id: e.target.value })}
            >
              <MenuItem value=""><em>Select a version</em></MenuItem>
              {versions.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.version} (model: {v.model_id})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Environment</InputLabel>
            <Select
              value={form.environment}
              label="Environment"
              onChange={(e) => setForm({ ...form, environment: e.target.value })}
            >
              <MenuItem value="development">Development</MenuItem>
              <MenuItem value="staging">Staging</MenuItem>
              <MenuItem value="production">Production</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Traffic Percentage"
            value={form.traffic_percentage}
            onChange={(e) => setForm({ ...form, traffic_percentage: e.target.value })}
            fullWidth
            type="number"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!form.model_version_id || creating}>
            {creating ? <CircularProgress size={20} /> : "Deploy"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
