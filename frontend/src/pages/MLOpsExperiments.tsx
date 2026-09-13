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
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Experiment {
  id: string;
  name: string;
  description: string;
  objective: string;
  dataset_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const statusColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  draft: "default",
  running: "info",
  completed: "success",
  failed: "error",
  cancelled: "default",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsExperiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    objective: "maximize_accuracy",
    dataset_id: "",
  });

  const fetchExperiments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ experiments: Experiment[] }>("/mlops/experiments");
      setExperiments(res.experiments || []);
    } catch (e: any) {
      setError(e.message || "Failed to load experiments");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    setError("");
    try {
      await rpost("/mlops/experiments", form);
      setDialogOpen(false);
      setForm({ name: "", description: "", objective: "maximize_accuracy", dataset_id: "" });
      await fetchExperiments();
    } catch (e: any) {
      setError(e.message || "Failed to create experiment");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Experiments</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchExperiments} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Create Experiment
          </Button>
        </Box>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Track and manage machine learning experiments
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : experiments.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Objective</TableCell>
                <TableCell>Dataset</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {experiments.map((exp) => (
                <TableRow key={exp.id} hover sx={{ cursor: "pointer" }}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {exp.name}
                    </Typography>
                    {exp.description && (
                      <Typography variant="caption" color="text.secondary">
                        {exp.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell><Chip label={exp.objective} size="small" variant="outlined" /></TableCell>
                  <TableCell>{exp.dataset_id || "-"}</TableCell>
                  <TableCell>
                    <Chip label={exp.status} size="small" color={statusColor[exp.status] || "default"} />
                  </TableCell>
                  <TableCell>{exp.created_at ? new Date(exp.created_at).toLocaleDateString() : "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Experiment Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Experiment</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <TextField
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            fullWidth
            multiline
            rows={3}
          />
          <FormControl fullWidth>
            <InputLabel>Objective</InputLabel>
            <Select
              value={form.objective}
              label="Objective"
              onChange={(e) => setForm({ ...form, objective: e.target.value })}
            >
              <MenuItem value="maximize_accuracy">Maximize Accuracy</MenuItem>
              <MenuItem value="minimize_loss">Minimize Loss</MenuItem>
              <MenuItem value="maximize_f1">Maximize F1</MenuItem>
              <MenuItem value="maximize_auc">Maximize AUC</MenuItem>
              <MenuItem value="minimize_rmse">Minimize RMSE</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Dataset ID"
            value={form.dataset_id}
            onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}
            fullWidth
            placeholder="Optional dataset reference"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!form.name.trim() || creating}>
            {creating ? <CircularProgress size={20} /> : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
