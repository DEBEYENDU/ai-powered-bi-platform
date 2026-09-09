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
  Divider,
  LinearProgress,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import WarningIcon from "@mui/icons-material/Warning";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
import SpeedIcon from "@mui/icons-material/Speed";
import TimelineIcon from "@mui/icons-material/Timeline";
import BugReportIcon from "@mui/icons-material/BugReport";
import ChatIcon from "@mui/icons-material/Chat";
import SendIcon from "@mui/icons-material/Send";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Insight {
  id: string;
  type: string;
  title: string;
  description: string;
  evidence: string[];
  confidence: string;
  metric: string;
  current_value: number;
  previous_value: number | null;
  change_pct: number;
  impact: string;
}

interface Anomaly {
  id: string;
  type: string;
  title: string;
  description: string;
  severity: string;
  metric: string;
  expected_value: number;
  actual_value: number;
  deviation_pct: number;
  confidence: string;
  evidence: string[];
}

interface RootCause {
  factor: string;
  contribution_pct: number;
  explanation: string;
  evidence: string[];
}

interface Recommendation {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  expected_impact: string;
  evidence: string[];
  confidence: string;
  business_logic: string;
  action_items: string[];
}

interface ForecastPoint {
  date: string;
  value: number;
  lower_bound: number;
  upper_bound: number;
}

interface Forecast {
  metric: string;
  horizon_days: number;
  points: ForecastPoint[];
  trend: string;
  seasonality_detected: boolean;
  confidence: string;
  accuracy_score: number;
}

interface Summary {
  summary_type: string;
  content: string;
  key_metrics: any[];
  risks: string[];
  opportunities: string[];
  generated_at: string;
}

interface ChartExplanation {
  chart_id: string;
  title: string;
  meaning: string;
  action: string;
  importance: string;
  confidence: string;
}

interface AnalyzeResult {
  success: boolean;
  dashboard_id: string;
  summary: Summary | null;
  insights: Insight[];
  anomalies: Anomaly[];
  root_causes: RootCause[];
  recommendations: Recommendation[];
  forecast: Forecast | null;
  chart_explanations: ChartExplanation[];
  risk_score: number;
  opportunity_score: number;
  analysis_time_ms: number;
  error: string | null;
}

interface FollowUpResult {
  answer: string;
  confidence: string;
  evidence: string[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const confidenceColor = (c: string) => {
  if (c === "high") return "success";
  if (c === "medium") return "warning";
  return "error";
};

const severityColor = (s: string) => {
  if (s === "high") return "error";
  if (s === "medium") return "warning";
  return "info";
};

const priorityColor = (p: string) => {
  if (p === "critical") return "error";
  if (p === "high") return "warning";
  if (p === "medium") return "info";
  return "default";
};

const insightIcon = (type: string) => {
  if (type.includes("positive")) return <TrendingUpIcon sx={{ color: "success.main", fontSize: 20 }} />;
  if (type.includes("negative")) return <TrendingDownIcon sx={{ color: "error.main", fontSize: 20 }} />;
  if (type.includes("growth")) return <SpeedIcon sx={{ color: "info.main", fontSize: 20 }} />;
  return <LightbulbIcon sx={{ color: "warning.main", fontSize: 20 }} />;
};

/* ------------------------------------------------------------------ */
/*  Confidence Meter                                                   */
/* ------------------------------------------------------------------ */

function ConfidenceMeter({ value, label }: { value: number; label?: string }) {
  const color = value >= 70 ? "success" : value >= 40 ? "warning" : "error";
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      {label && (
        <Typography variant="caption" color="text.secondary" sx={{ minWidth: 60 }}>
          {label}
        </Typography>
      )}
      <Box sx={{ flex: 1 }}>
        <LinearProgress
          variant="determinate"
          value={Math.min(100, Math.max(0, value))}
          color={color}
          sx={{ height: 8, borderRadius: 4 }}
        />
      </Box>
      <Typography variant="caption" sx={{ minWidth: 36, textAlign: "right" }}>
        {Math.round(value)}%
      </Typography>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Score Card                                                         */
/* ------------------------------------------------------------------ */

function ScoreCard({
  title,
  score,
  icon,
  color,
}: {
  title: string;
  score: number;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 200 }}>
      <CardContent sx={{ textAlign: "center", py: 2 }}>
        <Box sx={{ color: `${color}.main`, mb: 1 }}>{icon}</Box>
        <Typography variant="h3" sx={{ fontWeight: 700, color: `${color}.main` }}>
          {score}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {title}
        </Typography>
        <ConfidenceMeter value={score} />
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Insight Card                                                       */
/* ------------------------------------------------------------------ */

function InsightCard({ insight }: { insight: Insight }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          {insightIcon(insight.type)}
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }} noWrap>
            {insight.title}
          </Typography>
          <Chip label={insight.type.replace(/_/g, " ")} size="small" variant="outlined" sx={{ fontSize: 10 }} />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {insight.description}
        </Typography>
        {insight.change_pct !== 0 && (
          <Box sx={{ display: "flex", gap: 1, mb: 1 }}>
            <Chip
              label={`${insight.change_pct > 0 ? "+" : ""}${insight.change_pct.toFixed(1)}%`}
              size="small"
              color={insight.change_pct > 0 ? "success" : "error"}
            />
            <Chip label={insight.confidence} size="small" color={confidenceColor(insight.confidence) as any} />
          </Box>
        )}
        {insight.impact && (
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
            Impact: {insight.impact}
          </Typography>
        )}
        {insight.evidence.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {insight.evidence.slice(0, 2).map((e, i) => (
              <Typography key={i} variant="caption" sx={{ display: "block" }} color="text.secondary">
                - {e}
              </Typography>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Anomaly Card                                                       */
/* ------------------------------------------------------------------ */

function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  return (
    <Card variant="outlined" sx={{ borderLeft: 4, borderColor: `${severityColor(anomaly.severity)}.main` }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <BugReportIcon sx={{ color: `${severityColor(anomaly.severity)}.main`, fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }} noWrap>
            {anomaly.title}
          </Typography>
          <Chip label={anomaly.severity} size="small" color={severityColor(anomaly.severity) as any} />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {anomaly.description}
        </Typography>
        <Box sx={{ display: "flex", gap: 1, mb: 1 }}>
          <Chip label={anomaly.type.replace(/_/g, " ")} size="small" variant="outlined" sx={{ fontSize: 10 }} />
          {anomaly.deviation_pct !== 0 && (
            <Chip
              label={`${anomaly.deviation_pct > 0 ? "+" : ""}${anomaly.deviation_pct.toFixed(1)}% deviation`}
              size="small"
              variant="outlined"
            />
          )}
        </Box>
        {anomaly.evidence.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {anomaly.evidence.slice(0, 2).map((e, i) => (
              <Typography key={i} variant="caption" sx={{ display: "block" }} color="text.secondary">
                - {e}
              </Typography>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Recommendation Card                                                */
/* ------------------------------------------------------------------ */

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <LightbulbIcon sx={{ color: "warning.main", fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
            {rec.title}
          </Typography>
          <Chip label={rec.priority} size="small" color={priorityColor(rec.priority) as any} />
          <Chip label={rec.category} size="small" variant="outlined" />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {rec.description}
        </Typography>
        {rec.expected_impact && (
          <Alert severity="success" sx={{ py: 0, mb: 1, fontSize: "0.75rem" }}>
            Expected impact: {rec.expected_impact}
          </Alert>
        )}
        <Box sx={{ display: "flex", gap: 0.5, mb: 1 }}>
          <Chip label={rec.confidence} size="small" color={confidenceColor(rec.confidence) as any} />
        </Box>
        {expanded && rec.action_items.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, display: "block", mb: 0.5 }}>
              Action Items:
            </Typography>
            {rec.action_items.map((item, i) => (
              <Typography key={i} variant="caption" sx={{ display: "block" }} color="text.secondary">
                {i + 1}. {item}
              </Typography>
            ))}
          </Box>
        )}
        <Button size="small" onClick={() => setExpanded(!expanded)} sx={{ mt: 0.5 }}>
          {expanded ? "Show less" : "Show details"}
        </Button>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Forecast Chart                                                     */
/* ------------------------------------------------------------------ */

function ForecastChart({ forecast }: { forecast: Forecast }) {
  const chartData = forecast.points.map((p, i) => ({
    name: `Day ${i + 1}`,
    value: p.value,
    lower: p.lower_bound,
    upper: p.upper_bound,
  }));

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <TimelineIcon sx={{ color: "primary.main", fontSize: 20 }} />
          <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            Forecast: {forecast.metric}
          </Typography>
          <Chip label={`${forecast.horizon_days} days`} size="small" />
          <Chip
            label={forecast.trend}
            size="small"
            color={forecast.trend === "up" ? "success" : forecast.trend === "down" ? "error" : "default"}
          />
          {forecast.seasonality_detected && (
            <Chip label="seasonal" size="small" color="info" variant="outlined" />
          )}
        </Box>
        <Box sx={{ height: 250 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <RechartsTooltip />
              <Area type="monotone" dataKey="upper" stroke="none" fill="#e3f2fd" name="Upper bound" />
              <Area type="monotone" dataKey="lower" stroke="none" fill="#ffffff" name="Lower bound" />
              <Line type="monotone" dataKey="value" stroke="#1976d2" strokeWidth={2} dot={false} name="Forecast" />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
        <Box sx={{ mt: 1, display: "flex", gap: 1 }}>
          <ConfidenceMeter value={forecast.accuracy_score * 100} label="Accuracy" />
        </Box>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Follow-up Section                                                  */
/* ------------------------------------------------------------------ */

function FollowUpSection({ dashboardId }: { dashboardId: string }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FollowUpResult | null>(null);
  const [history, setHistory] = useState<{ q: string; r: FollowUpResult }[]>([]);

  const handleAsk = useCallback(async () => {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setQuestion("");
    try {
      const res = await rpost<FollowUpResult>("/ai/analyze/followup", {
        dashboard_id: dashboardId,
        question: q,
      });
      setResult(res);
      setHistory((prev) => [{ q, r: res }, ...prev]);
    } catch (e: any) {
      setResult({ answer: `Error: ${e}`, confidence: "low", evidence: [] });
    } finally {
      setLoading(false);
    }
  }, [question, loading, dashboardId]);

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <ChatIcon sx={{ color: "primary.main" }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Follow-up Questions
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder='e.g. "Why did revenue fall?" or "Compare this month with last month"'
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
            disabled={loading}
          />
          <Button
            variant="contained"
            onClick={handleAsk}
            disabled={!question.trim() || loading}
            startIcon={loading ? <CircularProgress size={16} /> : <SendIcon />}
          >
            Ask
          </Button>
        </Box>

        {result && (
          <Alert severity={result.confidence === "high" ? "success" : "info"} sx={{ mb: 2 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
          </Alert>
        )}

        {history.length > 1 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
              Previous questions:
            </Typography>
            {history.slice(1, 5).map((h, i) => (
              <Box key={i} sx={{ mb: 1, p: 1, bgcolor: "grey.50", borderRadius: 1 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, display: "block" }}>
                  Q: {h.q}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  A: {h.r.answer.slice(0, 120)}...
                </Typography>
              </Box>
            ))}
          </Box>
        )}

        <Box sx={{ mt: 2, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {[
            "Why did revenue fall?",
            "Explain this KPI",
            "What should I improve?",
            "Compare this month with last month",
          ].map((q) => (
            <Chip
              key={q}
              label={q}
              size="small"
              variant="outlined"
              onClick={() => setQuestion(q)}
              sx={{ cursor: "pointer" }}
            />
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export function BusinessInsights() {
  const [dashboardId, setDashboardId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = useCallback(async () => {
    const id = dashboardId.trim();
    if (!id || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await rpost<AnalyzeResult>("/ai/analyze", {
        dashboard_id: id,
        forecast_days: 30,
        include_recommendations: true,
        include_anomalies: true,
        include_forecast: true,
      });
      setResult(res);
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [dashboardId, loading]);

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", p: 2 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <AutorenewIcon sx={{ fontSize: 32, color: "primary.main" }} />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Business Insights
          </Typography>
          <Typography variant="body2" color="text.secondary">
            AI-powered analysis of your dashboards
          </Typography>
        </Box>
      </Box>

      {/* Input */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          <TextField
            fullWidth
            size="small"
            label="Dashboard ID"
            placeholder="Enter dashboard ID to analyse"
            value={dashboardId}
            onChange={(e) => setDashboardId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAnalyze();
            }}
            disabled={loading}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <Button
            variant="contained"
            onClick={handleAnalyze}
            disabled={!dashboardId.trim() || loading}
            startIcon={loading ? <CircularProgress size={16} /> : <AutorenewIcon />}
          >
            {loading ? "Analysing..." : "Analyse"}
          </Button>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading && !result && (
        <Box sx={{ textAlign: "center", mt: 8 }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Running statistical analysis, anomaly detection, forecasting, and AI reasoning...
          </Typography>
        </Box>
      )}

      {!result && !loading && (
        <Box sx={{ textAlign: "center", mt: 8, color: "text.secondary" }}>
          <AutorenewIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
          <Typography variant="h5" gutterBottom>
            AI Business Analyst
          </Typography>
          <Typography variant="body2">
            Enter a dashboard ID to automatically generate insights, detect anomalies,
            forecast trends, and get actionable recommendations.
          </Typography>
        </Box>
      )}

      {result && !result.success && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {result.error || "Analysis failed"}
        </Alert>
      )}

      {result && result.success && (
        <Box>
          {/* Scores */}
          <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
            <ScoreCard
              title="Risk Score"
              score={result.risk_score}
              icon={<WarningIcon sx={{ fontSize: 32 }} />}
              color="error"
            />
            <ScoreCard
              title="Opportunity Score"
              score={result.opportunity_score}
              icon={<TrendingUpIcon sx={{ fontSize: 32 }} />}
              color="success"
            />
            <Card variant="outlined" sx={{ flex: 1, minWidth: 200 }}>
              <CardContent sx={{ textAlign: "center", py: 2 }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: "primary.main" }}>
                  {result.insights.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Insights Generated
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined" sx={{ flex: 1, minWidth: 200 }}>
              <CardContent sx={{ textAlign: "center", py: 2 }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: "warning.main" }}>
                  {result.anomalies.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Anomalies Detected
                </Typography>
              </CardContent>
            </Card>
          </Box>

          {/* Executive Summary */}
          {result.summary && (
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                  Executive Summary
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.summary.content}
                </ReactMarkdown>
                {result.summary.risks.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="error.main" sx={{ mb: 0.5 }}>
                      Key Risks
                    </Typography>
                    {result.summary.risks.map((r, i) => (
                      <Typography key={i} variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                        - {r}
                      </Typography>
                    ))}
                  </Box>
                )}
                {result.summary.opportunities.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="success.main" sx={{ mb: 0.5 }}>
                      Opportunities
                    </Typography>
                    {result.summary.opportunities.map((o, i) => (
                      <Typography key={i} variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                        - {o}
                      </Typography>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* Insights */}
          {result.insights.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                AI Insights
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 2 }}>
                {result.insights.map((insight) => (
                  <InsightCard key={insight.id} insight={insight} />
                ))}
              </Box>
            </Box>
          )}

          {/* Forecasts */}
          {result.forecast && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Forecast
              </Typography>
              <ForecastChart forecast={result.forecast} />
            </Box>
          )}

          {/* Recommendations */}
          {result.recommendations.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Recommendations
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: 2 }}>
                {result.recommendations.map((rec) => (
                  <RecommendationCard key={rec.id} rec={rec} />
                ))}
              </Box>
            </Box>
          )}

          {/* Anomalies */}
          {result.anomalies.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Detected Anomalies
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: 2 }}>
                {result.anomalies.map((anomaly) => (
                  <AnomalyCard key={anomaly.id} anomaly={anomaly} />
                ))}
              </Box>
            </Box>
          )}

          {/* Root Causes */}
          {result.root_causes.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Root Cause Analysis
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: 2 }}>
                {result.root_causes.map((rc, i) => (
                  <Card key={i} variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        {rc.factor}
                      </Typography>
                      <ConfidenceMeter value={rc.contribution_pct} label="Contribution" />
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        {rc.explanation}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            </Box>
          )}

          {/* Chart Explanations */}
          {result.chart_explanations.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Chart Explanations
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: 2 }}>
                {result.chart_explanations.map((ce) => (
                  <Card key={ce.chart_id} variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        {ce.title}
                      </Typography>
                      {ce.meaning && (
                        <Box sx={{ mb: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, display: "block" }}>
                            What does this chart mean?
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {ce.meaning}
                          </Typography>
                        </Box>
                      )}
                      {ce.action && (
                        <Box sx={{ mb: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, display: "block" }}>
                            What should I do?
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {ce.action}
                          </Typography>
                        </Box>
                      )}
                      {ce.importance && (
                        <Box sx={{ mb: 1 }}>
                          <Typography variant="caption" sx={{ fontWeight: 600, display: "block" }}>
                            How important is it?
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {ce.importance}
                          </Typography>
                        </Box>
                      )}
                      <Chip
                        label={ce.confidence}
                        size="small"
                        color={confidenceColor(ce.confidence) as any}
                        sx={{ mt: 1 }}
                      />
                    </CardContent>
                  </Card>
                ))}
              </Box>
            </Box>
          )}

          {/* Follow-up */}
          <FollowUpSection dashboardId={result.dashboard_id} />

          {/* Timing */}
          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
            Analysis completed in {result.analysis_time_ms.toFixed(0)}ms
          </Typography>
        </Box>
      )}
    </Box>
  );
}
