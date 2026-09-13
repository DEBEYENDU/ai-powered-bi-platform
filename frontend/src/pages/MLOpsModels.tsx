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
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useNavigate } from "react-router-dom";
import { rget, rpost, rdel } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Model {
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
  failed: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsModels() {
  const navigate = useNavigate();
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    model_type: "classification",
    task_type: "binary_classification",
    framework: "scikit-learn",
  });

  const fetchModels = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ models: Model[] }>("/mlops/models");
      setModels(res.models || []);
    } catch (e: any) {
      setError(e.message || "Failed to load models");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    setError("");
    try {
      await rpost("/mlops/models", form);
      setDialogOpen(false);
      setForm({ name: "", description: "", model_type: "classification", task_type: "binary_classification", framework: "scikit-learn" });
      await fetchModels();
    } catch (e: any) {
      setError(e.message || "Failed to create model");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (modelId: string) => {
    if (!confirm("Delete this model?")) return;
    try {
      await rdel(`/mlops/models/${modelId}`);
      await fetchModels();
    } catch (e: any) {
      setError(e.message || "Failed to delete model");
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Model Registry</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchModels} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Create Model
          </Button>
        </Box>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Register and manage machine learning models
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : models.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Framework</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Owner</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {models.map((m) => (
                <TableRow key={m.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {m.name}
                    </Typography>
                  </TableCell>
                  <TableCell><Chip label={m.model_type} size="small" variant="outlined" /></TableCell>
                  <TableCell>{m.framework || "-"}</TableCell>
                  <TableCell>
                    <Chip label={m.status} size="small" color={statusColor[m.status] || "default"} />
                  </TableCell>
                  <TableCell>{m.owner || "-"}</TableCell>
                  <TableCell>{m.created_at ? new Date(m.created_at).toLocaleDateString() : "-"}</TableCell>
                  <TableCell align="center">
                    <Tooltip title="View">
                      <IconButton size="small" onClick={() => navigate(`/mlops/models/${m.id}`)}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" onClick={() => handleDelete(m.id)} color="error">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Model Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Model</DialogTitle>
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
            <InputLabel>Model Type</InputLabel>
            <Select
              value={form.model_type}
              label="Model Type"
              onChange={(e) => setForm({ ...form, model_type: e.target.value })}
            >
              <MenuItem value="classification">Classification</MenuItem>
              <MenuItem value="regression">Regression</MenuItem>
              <MenuItem value="clustering">Clustering</MenuItem>
              <MenuItem value="deep_learning">Deep Learning</MenuItem>
              <MenuItem value="nlp">NLP</MenuItem>
              <MenuItem value="recommendation">Recommendation</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Task Type</InputLabel>
            <Select
              value={form.task_type}
              label="Task Type"
              onChange={(e) => setForm({ ...form, task_type: e.target.value })}
            >
              <MenuItem value="binary_classification">Binary Classification</MenuItem>
              <MenuItem value="multi_class_classification">Multi-class Classification</MenuItem>
              <MenuItem value="regression">Regression</MenuItem>
              <MenuItem value="ranking">Ranking</MenuItem>
              <MenuItem value="segmentation">Segmentation</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Framework</InputLabel>
            <Select
              value={form.framework}
              label="Framework"
              onChange={(e) => setForm({ ...form, framework: e.target.value })}
            >
              <MenuItem value="scikit-learn">Scikit-learn</MenuItem>
              <MenuItem value="xgboost">XGBoost</MenuItem>
              <MenuItem value="lightgbm">LightGBM</MenuItem>
              <MenuItem value="pytorch">PyTorch</MenuItem>
              <MenuItem value="tensorflow">TensorFlow</MenuItem>
              <MenuItem value="keras">Keras</MenuItem>
            </Select>
          </FormControl>
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
