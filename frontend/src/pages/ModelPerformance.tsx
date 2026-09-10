/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Grid, LinearProgress,
  MenuItem, Paper, Select, TextField, Typography,
} from "@mui/material";
import MonitorHeartIcon from "@mui/icons-material/MonitorHeart";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorIcon from "@mui/icons-material/Error";
import { rpost } from "../api";

interface DriftAlert {
  drift_type: string; severity: string; feature: string;
  description: string; recommended_action: string;
  metrics: Record<string, number>;
}
interface MonitorResult {
  success: boolean; model_id: string;
  data_drift: DriftAlert[]; model_drift: DriftAlert[]; prediction_drift: DriftAlert[];
  overall_health: string; retraining_recommended: boolean;
  error: string | null;
}

function HealthIcon({ health }: { health: string }) {
  if (health === "healthy") return <CheckCircleIcon sx={{ color: "success.main", fontSize: 48 }} />;
  if (health === "warning") return <WarningAmberIcon sx={{ color: "warning.main", fontSize: 48 }} />;
  return <ErrorIcon sx={{ color: "error.main", fontSize: 48 }} />;
}

export function ModelPerformance() {
  const [modelId, setModelId] = useState("");
  const [lookback, setLookback] = useState("30");
  const [result, setResult] = useState<MonitorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleMonitor = async () => {
    if (!modelId) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await rpost<MonitorResult>("/ai/predictions/monitor", {
        model_id: modelId, lookback_days: parseInt(lookback),
      });
      setResult(res);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const allDrifts = [
    ...(result?.data_drift || []),
    ...(result?.model_drift || []),
    ...(result?.prediction_drift || []),
  ];

  const healthColor: Record<string, "success" | "warning" | "error"> = {
    healthy: "success", warning: "warning", critical: "error",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Model Performance</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Monitor model health, detect drift, and track performance over time
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 5 }}>
            <TextField fullWidth label="Model ID" value={modelId} onChange={(e) => setModelId(e.target.value)} />
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField fullWidth label="Lookback (days)" value={lookback} onChange={(e) => setLookback(e.target.value)} type="number" />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Button variant="contained" onClick={handleMonitor} disabled={!modelId || loading}
              startIcon={loading ? <CircularProgress size={18} /> : <MonitorHeartIcon />} fullWidth>
              {loading ? "Monitoring..." : "Run Monitoring"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {result && (
        <>
          {/* Health Card */}
          <Paper sx={{ p: 3, mb: 3, textAlign: "center" }}>
            <HealthIcon health={result.overall_health} />
            <Typography variant="h5" sx={{ mt: 1, fontWeight: 700 }}>
              Model is {result.overall_health}
            </Typography>
            {result.retraining_recommended && (
              <Alert severity="warning" sx={{ mt: 2, justifyContent: "center" }}>
                Retraining recommended — drift detected
              </Alert>
            )}
          </Paper>

          {/* Drift Summary */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 4 }}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="caption" color="text.secondary">Data Drift</Typography>
                  <Typography variant="h4">{result.data_drift?.length || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 4 }}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="caption" color="text.secondary">Model Drift</Typography>
                  <Typography variant="h4">{result.model_drift?.length || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 4 }}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="caption" color="text.secondary">Prediction Drift</Typography>
                  <Typography variant="h4">{result.prediction_drift?.length || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Drift Details */}
          {allDrifts.length > 0 && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>Drift Alerts ({allDrifts.length})</Typography>
              {allDrifts.map((d, i) => (
                <Alert key={i} severity={d.severity === "high" ? "error" : d.severity === "medium" ? "warning" : "info"} sx={{ mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    <Chip label={d.drift_type} size="small" sx={{ mr: 1 }} />
                    {d.feature}: {d.description}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{d.recommended_action}</Typography>
                </Alert>
              ))}
            </Paper>
          )}

          {allDrifts.length === 0 && (
            <Paper sx={{ p: 4, textAlign: "center" }}>
              <CheckCircleIcon sx={{ fontSize: 48, color: "success.main", mb: 1 }} />
              <Typography color="text.secondary">No drift detected — model is healthy</Typography>
            </Paper>
          )}
        </>
      )}
    </Box>
  );
}
