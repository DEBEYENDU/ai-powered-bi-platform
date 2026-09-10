/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import {
  Alert, Box, Button, Chip, CircularProgress, Grid, IconButton, MenuItem, Paper, Select,
  TextField, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { rpost } from "../api";

interface ScenarioVariable { name: string; change_type: string; value: string }

export function ScenarioAnalysis() {
  const [datasetId, setDatasetId] = useState("");
  const [target, setTarget] = useState("");
  const [horizon, setHorizon] = useState("30_days");
  const [variables, setVariables] = useState<ScenarioVariable[]>([
    { name: "", change_type: "percentage", value: "" },
  ]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const addVariable = () => setVariables((prev) => [...prev, { name: "", change_type: "percentage", value: "" }]);
  const removeVariable = (idx: number) => setVariables((prev) => prev.filter((_, i) => i !== idx));
  const updateVariable = (idx: number, field: string, val: string) =>
    setVariables((prev) => prev.map((v, i) => (i === idx ? { ...v, [field]: val } : v)));

  const handleRun = async () => {
    if (!datasetId || !target) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const vars: Record<string, any> = {};
      variables.forEach((v) => { if (v.name && v.value) vars[v.name] = { type: v.change_type, value: parseFloat(v.value) }; });
      const res = await rpost("/ai/predictions/whatif", {
        dataset_id: datasetId, target, variables: vars, horizon,
      });
      setResult(res);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Scenario Analysis</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        What-if analysis — simulate changes and predict business impact
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField fullWidth label="Dataset ID" value={datasetId} onChange={(e) => setDatasetId(e.target.value)} />
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <TextField fullWidth label="Target" value={target} onChange={(e) => setTarget(e.target.value)} />
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <Select fullWidth value={horizon} onChange={(e) => setHorizon(e.target.value)}>
              <MenuItem value="7_days">7 Days</MenuItem>
              <MenuItem value="30_days">30 Days</MenuItem>
              <MenuItem value="90_days">90 Days</MenuItem>
              <MenuItem value="365_days">1 Year</MenuItem>
            </Select>
          </Grid>
        </Grid>
      </Paper>

      {/* Variables */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
          <Typography variant="h6">Variables to Change</Typography>
          <Button size="small" startIcon={<AddIcon />} onClick={addVariable}>Add Variable</Button>
        </Box>
        {variables.map((v, idx) => (
          <Grid container spacing={1} key={idx} sx={{ mb: 1, alignItems: "center" }}>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField fullWidth size="small" label="Variable name (e.g. marketing_budget)"
                value={v.name} onChange={(e) => updateVariable(idx, "name", e.target.value)} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Select fullWidth size="small" value={v.change_type} onChange={(e) => updateVariable(idx, "change_type", e.target.value)}>
                <MenuItem value="percentage">Percentage (%)</MenuItem>
                <MenuItem value="absolute">Absolute Value</MenuItem>
                <MenuItem value="multiplier">Multiplier (x)</MenuItem>
              </Select>
            </Grid>
            <Grid size={{ xs: 5, md: 4 }}>
              <TextField fullWidth size="small" label="Value" type="number"
                value={v.value} onChange={(e) => updateVariable(idx, "value", e.target.value)} />
            </Grid>
            <Grid size={{ xs: 1, md: 1 }}>
              <IconButton size="small" onClick={() => removeVariable(idx)}><DeleteIcon fontSize="small" /></IconButton>
            </Grid>
          </Grid>
        ))}
      </Paper>

      <Button variant="contained" onClick={handleRun} disabled={!datasetId || !target || loading}
        startIcon={loading ? <CircularProgress size={18} /> : <PlayArrowIcon />} sx={{ mb: 3 }}>
        {loading ? "Running Analysis..." : "Run What-If Analysis"}
      </Button>

      {/* Result */}
      {result?.success && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Analysis Results</Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            {typeof result.analysis === "string" ? result.analysis : JSON.stringify(result.analysis, null, 2)}
          </Alert>
        </Paper>
      )}
    </Box>
  );
}
