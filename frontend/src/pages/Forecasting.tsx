/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart, Legend, ReferenceLine } from "recharts";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Dataset { dataset_id: string; name: string; row_count: number }
interface ForecastPoint { date: string; value: number; lower_bound: number; upper_bound: number; best_case: number; worst_case: number }
interface PredictionResult {
  success: boolean; prediction_id: string; target: string; model_type: string;
  predictions: ForecastPoint[]; overall_confidence: number; trend: string;
  growth_percentage: number; risk_score: number;
  metrics: { mae?: number; rmse?: number; mape?: number; r2?: number };
  explainability: { feature_importances: any[]; business_interpretation: string; top_factors: string[] };
  recommendations: { category: string; recommendation: string; impact: string; priority: string; confidence: string }[];
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "increasing") return <TrendingUpIcon sx={{ color: "success.main" }} />;
  if (trend === "decreasing") return <TrendingDownIcon sx={{ color: "error.main" }} />;
  return <TrendingFlatIcon sx={{ color: "text.secondary" }} />;
}

function ScoreCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <Card>
      <CardContent sx={{ textAlign: "center" }}>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
        <Typography variant="h5" sx={{ fontWeight: 700, color: color || "text.primary" }}>{value}</Typography>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function Forecasting() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [target, setTarget] = useState("");
  const [horizon, setHorizon] = useState("30_days");
  const [modelType, setModelType] = useState("");
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"chart" | "details" | "recommendations">("chart");

  useEffect(() => {
    rget<{ datasets: Dataset[] }>("/ai/de/datasets")
      .then((res) => setDatasets(res.datasets || []))
      .catch((e) => setError(e.message));
  }, []);

  const handleForecast = async () => {
    if (!selectedId || !target) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await rpost<PredictionResult>("/ai/predictions/predict", {
        dataset_id: selectedId,
        target,
        horizon,
        model_type: modelType || undefined,
        include_explanation: true,
        include_recommendations: true,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Forecast failed");
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.predictions?.map((p, i) => ({
    name: p.date || `Day ${i + 1}`,
    value: p.value,
    lower: p.lower_bound,
    upper: p.upper_bound,
    best: p.best_case,
    worst: p.worst_case,
  })) || [];

  const priorityColor: Record<string, "error" | "warning" | "info" | "default"> = {
    critical: "error", high: "warning", medium: "info", low: "default",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Forecasting</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Generate AI-powered forecasts with confidence intervals and recommendations
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Select fullWidth value={selectedId} onChange={(e) => setSelectedId(e.target.value)} displayEmpty>
              <MenuItem value=""><em>Select dataset</em></MenuItem>
              {datasets.map((ds) => (
                <MenuItem key={ds.dataset_id} value={ds.dataset_id}>{ds.name}</MenuItem>
              ))}
            </Select>
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <TextField fullWidth label="Target column" value={target} onChange={(e) => setTarget(e.target.value)} />
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <Select fullWidth value={horizon} onChange={(e) => setHorizon(e.target.value)}>
              <MenuItem value="7_days">7 Days</MenuItem>
              <MenuItem value="30_days">30 Days</MenuItem>
              <MenuItem value="90_days">90 Days</MenuItem>
              <MenuItem value="365_days">1 Year</MenuItem>
            </Select>
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <Select fullWidth value={modelType} onChange={(e) => setModelType(e.target.value)} displayEmpty>
              <MenuItem value=""><em>Auto Select</em></MenuItem>
              <MenuItem value="prophet">Prophet</MenuItem>
              <MenuItem value="arima">ARIMA</MenuItem>
              <MenuItem value="sarima">SARIMA</MenuItem>
              <MenuItem value="random_forest">Random Forest</MenuItem>
              <MenuItem value="xgboost">XGBoost</MenuItem>
              <MenuItem value="lightgbm">LightGBM</MenuItem>
            </Select>
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <Button variant="contained" onClick={handleForecast} disabled={!selectedId || !target || loading}
              startIcon={loading ? <CircularProgress size={18} /> : <ShowChartIcon />} fullWidth>
              {loading ? "Forecasting..." : "Generate Forecast"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Results */}
      {result && (
        <>
          {/* Score Cards */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 6, md: 2 }}>
              <ScoreCard label="Confidence" value={`${(result.overall_confidence * 100).toFixed(0)}%`}
                color={result.overall_confidence > 0.8 ? "success.main" : "warning.main"} />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <ScoreCard label="Trend" value={result.trend} />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <ScoreCard label="Growth" value={`${result.growth_percentage > 0 ? "+" : ""}${result.growth_percentage.toFixed(1)}%`}
                color={result.growth_percentage > 0 ? "success.main" : "error.main"} />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <ScoreCard label="Risk Score" value={result.risk_score}
                color={result.risk_score > 60 ? "error.main" : result.risk_score > 30 ? "warning.main" : "success.main"} />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <ScoreCard label="RMSE" value={result.metrics?.rmse?.toFixed(2) ?? "-"} />
            </Grid>
            <Grid size={{ xs: 6, md: 2 }}>
              <ScoreCard label="R²" value={result.metrics?.r2?.toFixed(3) ?? "-"} />
            </Grid>
          </Grid>

          {/* Tabs */}
          <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
            {(["chart", "details", "recommendations"] as const).map((tab) => (
              <Button key={tab} variant={activeTab === tab ? "contained" : "outlined"}
                onClick={() => setActiveTab(tab)} size="small">
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </Button>
            ))}
          </Box>

          {/* Chart Tab */}
          {activeTab === "chart" && chartData.length > 0 && (
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>Forecast — {result.target}</Typography>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="upper" stroke="#8884d8" fill="#8884d8" fillOpacity={0.1} name="Upper Bound" />
                  <Area type="monotone" dataKey="lower" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.1} name="Lower Bound" />
                  <Line type="monotone" dataKey="value" stroke="#1976d2" strokeWidth={2} dot={false} name="Forecast" />
                  <Line type="monotone" dataKey="best" stroke="#4caf50" strokeWidth={1} strokeDasharray="5 5" dot={false} name="Best Case" />
                  <Line type="monotone" dataKey="worst" stroke="#f44336" strokeWidth={1} strokeDasharray="5 5" dot={false} name="Worst Case" />
                </AreaChart>
              </ResponsiveContainer>
            </Paper>
          )}

          {/* Details Tab */}
          {activeTab === "details" && (
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" sx={{ mb: 1 }}>Model Explanation</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {result.explainability?.business_interpretation}
                  </Typography>
                  {result.explainability?.feature_importances?.length > 0 && (
                    <>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>Feature Importance</Typography>
                      {result.explainability.feature_importances.slice(0, 5).map((f, i) => (
                        <Box key={i} sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                          <Typography variant="body2">{f.feature}</Typography>
                  <Chip label={`${(f.importance * 100).toFixed(1)}%`} size="small" />
                        </Box>
                      ))}
                    </>
                  )}
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" sx={{ mb: 1 }}>Forecast Values</Typography>
                  <Box sx={{ maxHeight: 300, overflow: "auto" }}>
                    {result.predictions?.slice(0, 20).map((p, i) => (
                      <Box key={i} sx={{ display: "flex", justifyContent: "space-between", py: 0.5, borderBottom: "1px solid #eee" }}>
                        <Typography variant="body2">{p.date}</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{p.value.toFixed(2)}</Typography>
                        <Typography variant="body2" color="text.secondary">[{p.lower_bound.toFixed(1)}-{p.upper_bound.toFixed(1)}]</Typography>
                      </Box>
                    ))}
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          )}

          {/* Recommendations Tab */}
          {activeTab === "recommendations" && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>Business Recommendations</Typography>
              {result.recommendations?.map((rec, i) => (
                <Alert key={i} severity={rec.priority === "critical" ? "error" : rec.priority === "high" ? "warning" : "info"} sx={{ mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>[{rec.category}] {rec.recommendation}</Typography>
                  <Typography variant="caption" color="text.secondary">Impact: {rec.impact} | Priority: {rec.priority} | Confidence: {rec.confidence}</Typography>
                </Alert>
              ))}
            </Box>
          )}
        </>
      )}
    </Box>
  );
}
