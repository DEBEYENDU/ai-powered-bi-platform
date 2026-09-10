/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Chip, CircularProgress, Grid, MenuItem, Paper, Select,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { rget, rpost } from "../api";

interface Dataset { dataset_id: string; name: string; row_count: number }
interface TrainResult {
  success: boolean; model_id: string; model_type: string;
  metrics: { mae?: number; rmse?: number; mape?: number; r2?: number; accuracy?: number; f1?: number; roc_auc?: number; precision?: number; recall?: number };
  training_time_ms: number; error: string | null;
}
interface CompareResult {
  success: boolean; models: any[]; best_model: string; comparison_metric: string; error: string | null;
}

export function ModelManagement() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [target, setTarget] = useState("");
  const [modelType, setModelType] = useState("auto_ml");
  const [testSize, setTestSize] = useState("0.2");
  const [cvFolds, setCvFolds] = useState("5");
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    rget<{ datasets: Dataset[] }>("/ai/de/datasets")
      .then((res) => setDatasets(res.datasets || []))
      .catch((e) => setError(e.message));
  }, []);

  const handleTrain = async () => {
    if (!selectedId || !target) return;
    setLoading(true); setError(""); setTrainResult(null);
    try {
      const res = await rpost<TrainResult>("/ai/predictions/train", {
        dataset_id: selectedId, target, model_type: modelType,
        test_size: parseFloat(testSize), cross_validation_folds: parseInt(cvFolds),
      });
      setTrainResult(res);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleCompare = async () => {
    if (!selectedId || !target) return;
    setComparing(true); setError(""); setCompareResult(null);
    try {
      const res = await rpost<CompareResult>("/ai/predictions/compare", {
        dataset_id: selectedId, target,
        model_types: ["random_forest", "xgboost", "lightgbm", "linear"],
      });
      setCompareResult(res);
    } catch (e: any) { setError(e.message); }
    finally { setComparing(false); }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Model Management</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Train, compare, and manage machine learning models
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Select fullWidth value={selectedId} onChange={(e) => setSelectedId(e.target.value)} displayEmpty>
              <MenuItem value=""><em>Select dataset</em></MenuItem>
              {datasets.map((ds) => <MenuItem key={ds.dataset_id} value={ds.dataset_id}>{ds.name}</MenuItem>)}
            </Select>
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <TextField fullWidth label="Target" value={target} onChange={(e) => setTarget(e.target.value)} />
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <Select fullWidth value={modelType} onChange={(e) => setModelType(e.target.value)}>
              <MenuItem value="auto_ml">Auto ML</MenuItem>
              <MenuItem value="random_forest">Random Forest</MenuItem>
              <MenuItem value="xgboost">XGBoost</MenuItem>
              <MenuItem value="lightgbm">LightGBM</MenuItem>
              <MenuItem value="linear">Linear</MenuItem>
              <MenuItem value="ridge">Ridge</MenuItem>
            </Select>
          </Grid>
          <Grid size={{ xs: 6, md: 1 }}>
            <TextField fullWidth label="Test %" value={testSize} onChange={(e) => setTestSize(e.target.value)} size="small" />
          </Grid>
          <Grid size={{ xs: 6, md: 1 }}>
            <TextField fullWidth label="CV Folds" value={cvFolds} onChange={(e) => setCvFolds(e.target.value)} size="small" />
          </Grid>
          <Grid size={{ xs: 6, md: 1.5 }}>
            <Button variant="contained" onClick={handleTrain} disabled={!selectedId || !target || loading}
              startIcon={loading ? <CircularProgress size={16} /> : <AddIcon />} fullWidth>
              {loading ? "Training..." : "Train"}
            </Button>
          </Grid>
          <Grid size={{ xs: 6, md: 1.5 }}>
            <Button variant="outlined" onClick={handleCompare} disabled={!selectedId || !target || comparing} fullWidth>
              {comparing ? <CircularProgress size={16} /> : "Compare"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Train Result */}
      {trainResult && (
        <Alert severity={trainResult.success ? "success" : "error"} sx={{ mb: 2 }}>
          {trainResult.success ? (
            <>Model trained: {trainResult.model_type} | ID: {trainResult.model_id} | Time: {trainResult.training_time_ms}ms</>
          ) : trainResult.error}
        </Alert>
      )}

      {/* Comparison */}
      {compareResult?.success && compareResult.models.length > 0 && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Model Comparison
            <Chip label={`Best: ${compareResult.best_model}`} color="success" size="small" sx={{ ml: 1 }} />
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Model</TableCell>
                  <TableCell align="right">MAE</TableCell>
                  <TableCell align="right">RMSE</TableCell>
                  <TableCell align="right">R²</TableCell>
                  <TableCell align="right">MAPE</TableCell>
                  <TableCell align="right">CV Score</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {compareResult.models.map((m, i) => (
                  <TableRow key={i} hover sx={m.model_type === compareResult.best_model ? { bgcolor: "action.hover" } : {}}>
                    <TableCell><Chip label={m.model_type} size="small" color={m.model_type === compareResult.best_model ? "success" : "default"} /></TableCell>
                    <TableCell align="right">{m.metrics?.mae?.toFixed(4) ?? "-"}</TableCell>
                    <TableCell align="right">{m.metrics?.rmse?.toFixed(4) ?? "-"}</TableCell>
                    <TableCell align="right">{m.metrics?.r2?.toFixed(4) ?? "-"}</TableCell>
                    <TableCell align="right">{m.metrics?.mape?.toFixed(2) ?? "-"}%</TableCell>
                    <TableCell align="right">{m.metrics?.cross_val_score?.toFixed(4) ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
}
