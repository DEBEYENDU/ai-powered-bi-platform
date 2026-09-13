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
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorIcon from "@mui/icons-material/Error";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DriftCheckResult {
  success: boolean;
  drift_detected: boolean;
  drift_score: number;
  status: string;
  details: Record<string, any>;
  error: string | null;
}

interface DriftHistoryEntry {
  id: string;
  check_type: string;
  drift_score: number;
  status: string;
  details: Record<string, any>;
  created_at: string;
}

interface DriftSummary {
  total_checks: number;
  normal: number;
  warning: number;
  critical: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function DriftStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "critical":
      return <ErrorIcon sx={{ color: "error.main", fontSize: 18 }} />;
    case "warning":
      return <WarningAmberIcon sx={{ color: "warning.main", fontSize: 18 }} />;
    default:
      return <CheckCircleIcon sx={{ color: "success.main", fontSize: 18 }} />;
  }
}

const driftStatusColor: Record<string, "default" | "success" | "warning" | "error"> = {
  normal: "success",
  warning: "warning",
  critical: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MLOpsDrift() {
  const [history, setHistory] = useState<DriftHistoryEntry[]>([]);
  const [summary, setSummary] = useState<DriftSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dataResult, setDataResult] = useState<DriftCheckResult | null>(null);
  const [predResult, setPredResult] = useState<DriftCheckResult | null>(null);
  const [checkingData, setCheckingData] = useState(false);
  const [checkingPred, setCheckingPred] = useState(false);

  const [dataForm, setDataForm] = useState({
    reference_mean: "",
    reference_std: "",
    current_mean: "",
    current_std: "",
  });

  const [predForm, setPredForm] = useState({
    historical_predictions: "",
    recent_predictions: "",
  });

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [histRes, sumRes] = await Promise.allSettled([
        rget<{ history: DriftHistoryEntry[] }>("/mlops/drift/history"),
        rget<DriftSummary>("/mlops/drift/summary"),
      ]);
      if (histRes.status === "fulfilled") setHistory(histRes.value.history || []);
      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
    } catch (e: any) {
      setError(e.message || "Failed to load drift data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleDataDrift = async () => {
    if (!dataForm.reference_mean || !dataForm.current_mean) return;
    setCheckingData(true);
    setError("");
    setDataResult(null);
    try {
      const res = await rpost<DriftCheckResult>("/mlops/drift/check-data", {
        reference_stats: {
          mean: parseFloat(dataForm.reference_mean),
          std: parseFloat(dataForm.reference_std || "1"),
        },
        current_stats: {
          mean: parseFloat(dataForm.current_mean),
          std: parseFloat(dataForm.current_std || "1"),
        },
      });
      setDataResult(res);
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to check data drift");
    } finally {
      setCheckingData(false);
    }
  };

  const handlePredictionDrift = async () => {
    if (!predForm.historical_predictions || !predForm.recent_predictions) return;
    setCheckingPred(true);
    setError("");
    setPredResult(null);
    try {
      let historical: number[];
      let recent: number[];
      try {
        historical = JSON.parse(predForm.historical_predictions);
        recent = JSON.parse(predForm.recent_predictions);
      } catch {
        setError("Invalid JSON arrays for predictions");
        setCheckingPred(false);
        return;
      }
      const res = await rpost<DriftCheckResult>("/mlops/drift/check-prediction", {
        historical_predictions: historical,
        recent_predictions: recent,
      });
      setPredResult(res);
      await fetchAll();
    } catch (e: any) {
      setError(e.message || "Failed to check prediction drift");
    } finally {
      setCheckingPred(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Drift Detection</Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchAll} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Detect data and prediction drift in your models
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Total Checks</Typography>
              <Typography variant="h4" sx={{ fontWeight: 600 }}>{summary?.total_checks ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Normal</Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: "success.main" }}>{summary?.normal ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Warning</Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: "warning.main" }}>{summary?.warning ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Critical</Typography>
              <Typography variant="h4" sx={{ fontWeight: 600, color: "error.main" }}>{summary?.critical ?? 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Data Drift Check */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Check Data Drift</Typography>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField
              fullWidth
              label="Reference Mean"
              value={dataForm.reference_mean}
              onChange={(e) => setDataForm({ ...dataForm, reference_mean: e.target.value })}
              size="small"
              type="number"
            />
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField
              fullWidth
              label="Reference Std"
              value={dataForm.reference_std}
              onChange={(e) => setDataForm({ ...dataForm, reference_std: e.target.value })}
              size="small"
              type="number"
            />
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField
              fullWidth
              label="Current Mean"
              value={dataForm.current_mean}
              onChange={(e) => setDataForm({ ...dataForm, current_mean: e.target.value })}
              size="small"
              type="number"
            />
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <TextField
              fullWidth
              label="Current Std"
              value={dataForm.current_std}
              onChange={(e) => setDataForm({ ...dataForm, current_std: e.target.value })}
              size="small"
              type="number"
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Button
              variant="contained"
              onClick={handleDataDrift}
              disabled={!dataForm.reference_mean || !dataForm.current_mean || checkingData}
              fullWidth
            >
              {checkingData ? <CircularProgress size={20} /> : "Check Data Drift"}
            </Button>
          </Grid>
        </Grid>
        {dataResult && (
          <Alert severity={dataResult.drift_detected ? "warning" : "success"} sx={{ mt: 2 }}>
            {dataResult.drift_detected
              ? `Drift detected! Score: ${dataResult.drift_score.toFixed(4)} (${dataResult.status})`
              : `No drift detected. Score: ${dataResult.drift_score.toFixed(4)}`}
          </Alert>
        )}
      </Paper>

      {/* Prediction Drift Check */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Check Prediction Drift</Typography>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              fullWidth
              label="Historical Predictions (JSON array)"
              value={predForm.historical_predictions}
              onChange={(e) => setPredForm({ ...predForm, historical_predictions: e.target.value })}
              size="small"
              placeholder="[0.1, 0.2, 0.3, 0.4]"
              multiline
              rows={3}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              fullWidth
              label="Recent Predictions (JSON array)"
              value={predForm.recent_predictions}
              onChange={(e) => setPredForm({ ...predForm, recent_predictions: e.target.value })}
              size="small"
              placeholder="[0.2, 0.3, 0.4, 0.5]"
              multiline
              rows={3}
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Button
              variant="contained"
              onClick={handlePredictionDrift}
              disabled={!predForm.historical_predictions || !predForm.recent_predictions || checkingPred}
              fullWidth
            >
              {checkingPred ? <CircularProgress size={20} /> : "Check Prediction Drift"}
            </Button>
          </Grid>
        </Grid>
        {predResult && (
          <Alert severity={predResult.drift_detected ? "warning" : "success"} sx={{ mt: 2 }}>
            {predResult.drift_detected
              ? `Drift detected! Score: ${predResult.drift_score.toFixed(4)} (${predResult.status})`
              : `No drift detected. Score: ${predResult.drift_score.toFixed(4)}`}
          </Alert>
        )}
      </Paper>

      {/* Drift History */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>Drift History</Typography>
        {loading ? (
          <CircularProgress />
        ) : history.length === 0 ? (
          <Typography color="text.secondary">No data available yet.</Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell width={40}></TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Drift Score</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Details</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((h) => (
                  <TableRow key={h.id} hover>
                    <TableCell><DriftStatusIcon status={h.status} /></TableCell>
                    <TableCell><Chip label={h.check_type} size="small" variant="outlined" /></TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontFamily: "monospace", fontWeight: 600 }}>
                        {h.drift_score.toFixed(4)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={h.status} size="small" color={driftStatusColor[h.status] || "default"} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {JSON.stringify(h.details)}
                      </Typography>
                    </TableCell>
                    <TableCell>{h.created_at ? new Date(h.created_at).toLocaleString() : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
}
