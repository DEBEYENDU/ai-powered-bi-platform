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
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import SendIcon from "@mui/icons-material/Send";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import SaveIcon from "@mui/icons-material/Save";
import HistoryIcon from "@mui/icons-material/History";
import ChatIcon from "@mui/icons-material/Chat";
import TableChartIcon from "@mui/icons-material/TableChart";
import BarChartIcon from "@mui/icons-material/BarChart";
import TimelineIcon from "@mui/icons-material/Timeline";
import PieChartIcon from "@mui/icons-material/PieChart";
import ScatterPlotIcon from "@mui/icons-material/ScatterPlot";
import TextFieldsIcon from "@mui/icons-material/TextFields";
import SpeedIcon from "@mui/icons-material/Speed";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Widget {
  id: string;
  type: string;
  title: string;
  sql: string;
  explanation: string;
  chart: string;
  columns: string[];
  position: { x: number; y: number; w: number; h: number };
  config: any;
  reasoning: string;
}

interface GeneratedDashboard {
  success: boolean;
  dashboard_id: string | null;
  title: string;
  description: string;
  widgets: Widget[];
  layout: any;
  filters: any[];
  theme: any;
  generation_time_ms: number;
  error: string | null;
}

interface Template {
  id: string;
  title: string;
  prompt: string;
}

interface ExplainResult {
  id: string;
  explanation: string;
}

const WIDGET_ICONS: Record<string, any> = {
  kpi: SpeedIcon,
  line: TimelineIcon,
  bar: BarChartIcon,
  area: TimelineIcon,
  pie: PieChartIcon,
  donut: PieChartIcon,
  scatter: ScatterPlotIcon,
  table: TableChartIcon,
  text: TextFieldsIcon,
  gauge: SpeedIcon,
};

/* ------------------------------------------------------------------ */
/*  Widget Preview Card                                                */
/* ------------------------------------------------------------------ */

function WidgetCard({
  widget,
  selected,
  onSelect,
  onExplain,
  explanation,
}: {
  widget: Widget;
  selected: boolean;
  onSelect: () => void;
  onExplain: () => void;
  explanation?: string;
}) {
  const Icon = WIDGET_ICONS[widget.type] || BarChartIcon;
  const [showSQL, setShowSQL] = useState(false);

  return (
    <Card
      variant="outlined"
      onClick={onSelect}
      sx={{
        cursor: "pointer",
        border: selected ? 2 : 1,
        borderColor: selected ? "primary.main" : "divider",
        "&:hover": { borderColor: "primary.light" },
        height: "100%",
      }}
    >
      <CardContent sx={{ pb: "12px !important" }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
          <Icon sx={{ fontSize: 18, mr: 0.5, color: "primary.main" }} />
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }} noWrap>
            {widget.title}
          </Typography>
          <Chip label={widget.type} size="small" variant="outlined" sx={{ fontSize: 10 }} />
        </Box>

        {widget.sql && (
          <Box sx={{ mb: 1 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ cursor: "pointer", textDecoration: "underline" }}
              onClick={(e) => {
                e.stopPropagation();
                setShowSQL(!showSQL);
              }}
            >
              {showSQL ? "Hide SQL" : "View SQL"}
            </Typography>
            {showSQL && (
              <Paper variant="outlined" sx={{ mt: 0.5, p: 1, fontSize: "0.7rem", fontFamily: "monospace", overflow: "auto", maxHeight: 120 }}>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{widget.sql}</pre>
              </Paper>
            )}
          </Box>
        )}

        {widget.reasoning && (
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic", display: "block" }}>
            {widget.reasoning}
          </Typography>
        )}

        {explanation && (
          <Alert severity="info" sx={{ mt: 1, py: 0, fontSize: "0.75rem" }}>
            {explanation}
          </Alert>
        )}

        <Box sx={{ mt: 1, display: "flex", gap: 0.5 }}>
          <Tooltip title="Copy SQL">
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(widget.sql);
              }}
            >
              <ContentCopyIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Explain">
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onExplain();
              }}
            >
              <ChatIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        </Box>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Right Panel - Widget Properties                                    */
/* ------------------------------------------------------------------ */

function WidgetProperties({
  widget,
  explanation,
}: {
  widget: Widget | null;
  explanation?: string;
}) {
  if (!widget) {
    return (
      <Box sx={{ p: 2, textAlign: "center", color: "text.secondary" }}>
        <Typography variant="body2">Select a widget to view properties</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }} gutterBottom>
        {widget.title}
      </Typography>
      <Chip label={widget.type} size="small" color="primary" sx={{ mb: 1 }} />

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
        Chart Type
      </Typography>
      <Typography variant="body2">{widget.chart}</Typography>

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
        Columns
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {widget.columns.map((col) => (
          <Chip key={col} label={col} size="small" variant="outlined" />
        ))}
      </Box>

      {widget.reasoning && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            Reasoning
          </Typography>
          <Typography variant="body2" sx={{ fontStyle: "italic" }}>
            {widget.reasoning}
          </Typography>
        </>
      )}

      {explanation && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            AI Explanation
          </Typography>
          <Alert severity="info" sx={{ mt: 0.5, py: 0 }}>
            {explanation}
          </Alert>
        </>
      )}

      {widget.sql && (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            SQL Query
          </Typography>
          <Paper variant="outlined" sx={{ mt: 0.5, p: 1, fontSize: "0.75rem", fontFamily: "monospace", overflow: "auto", maxHeight: 300 }}>
            <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{widget.sql}</pre>
          </Paper>
        </>
      )}
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Main AIDashboardGenerator Page                                     */
/* ------------------------------------------------------------------ */

export function AIDashboardGenerator() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [dashboard, setDashboard] = useState<GeneratedDashboard | null>(null);
  const [selectedWidget, setSelectedWidget] = useState<Widget | null>(null);
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [templates, setTemplates] = useState<Template[]>([]);
  const [history, setHistory] = useState<GeneratedDashboard[]>([]);
  const [improvePrompt, setImprovePrompt] = useState("");
  const [improving, setImproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    rget<Template[]>("/ai/dashboard/templates").then(setTemplates).catch(() => {});
  }, []);

  const handleGenerate = useCallback(async () => {
    const q = prompt.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setPrompt("");

    try {
      const res = await rpost<GeneratedDashboard>("/ai/dashboard/generate", {
        prompt: q,
        save: true,
      });
      setDashboard(res);
      setHistory((prev) => [res, ...prev]);
      setSelectedWidget(null);
      setExplanations({});
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [prompt, loading]);

  const handleImprove = useCallback(async () => {
    if (!improvePrompt.trim() || !dashboard?.dashboard_id || improving) return;

    setImproving(true);
    setError(null);

    try {
      const res = await rpost<GeneratedDashboard>("/ai/dashboard/improve", {
        dashboard_id: dashboard.dashboard_id,
        instruction: improvePrompt.trim(),
      });
      setDashboard(res);
      setImprovePrompt("");
      setSelectedWidget(null);
    } catch (e: any) {
      setError(String(e));
    } finally {
      setImproving(false);
    }
  }, [improvePrompt, dashboard, improving]);

  const handleExplain = useCallback(async (widgetId: string) => {
    if (!dashboard?.dashboard_id) return;
    try {
      const res = await rpost<{ explanations: ExplainResult[] }>("/ai/dashboard/explain", {
        dashboard_id: dashboard.dashboard_id,
      });
      const map: Record<string, string> = {};
      for (const exp of res.explanations) {
        map[exp.id] = exp.explanation;
      }
      setExplanations(map);
    } catch {
      /* ignore */
    }
  }, [dashboard]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 64px - 48px)" }}>
      {/* Left Panel: Prompt + Templates + History */}
      <Box
        sx={{
          width: 300,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          borderRight: 1,
          borderColor: "divider",
          height: "100%",
        }}
      >
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="fullWidth">
          <Tab icon={<ChatIcon />} iconPosition="start" label="Generate" sx={{ minHeight: 40 }} />
          <Tab icon={<AddIcon />} iconPosition="start" label="Templates" sx={{ minHeight: 40 }} />
          <Tab icon={<HistoryIcon />} iconPosition="start" label="History" sx={{ minHeight: 40 }} />
        </Tabs>
        <Divider />

        {activeTab === 0 && (
          <Box sx={{ p: 1.5, flex: 1, overflow: "auto" }}>
            <Typography variant="caption" color="text.secondary">
              Describe your dashboard
            </Typography>
            <TextField
              multiline
              maxRows={6}
              placeholder="e.g. Create a sales dashboard with revenue trends and top products"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              fullWidth
              size="small"
              disabled={loading}
              sx={{ mt: 0.5, mb: 1 }}
            />
            <Button
              variant="contained"
              fullWidth
              onClick={handleGenerate}
              disabled={!prompt.trim() || loading}
              startIcon={loading ? <CircularProgress size={16} /> : <SendIcon />}
            >
              {loading ? "Generating..." : "Generate Dashboard"}
            </Button>

            {dashboard?.dashboard_id && (
              <Box sx={{ mt: 2 }}>
                <Divider sx={{ mb: 1 }} />
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  Improve this dashboard
                </Typography>
                <TextField
                  multiline
                  maxRows={4}
                  placeholder='e.g. "Make it more executive" or "Add customer metrics"'
                  value={improvePrompt}
                  onChange={(e) => setImprovePrompt(e.target.value)}
                  fullWidth
                  size="small"
                  disabled={improving}
                  sx={{ mt: 0.5, mb: 1 }}
                />
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={handleImprove}
                  disabled={!improvePrompt.trim() || improving}
                  startIcon={improving ? <CircularProgress size={16} /> : <AutoFixHighIcon />}
                  size="small"
                >
                  {improving ? "Improving..." : "Improve Dashboard"}
                </Button>
              </Box>
            )}
          </Box>
        )}

        {activeTab === 1 && (
          <List sx={{ flex: 1, overflow: "auto", py: 0 }}>
            {templates.map((t) => (
              <ListItemButton
                key={t.id}
                onClick={() => {
                  setPrompt(t.prompt);
                  setActiveTab(0);
                }}
              >
                <ListItemText
                  primary={t.title}
                  secondary={t.prompt}
                  slotProps={{
                    primary: { variant: "body2" as const },
                    secondary: { variant: "caption" as const, noWrap: true },
                  }}
                />
              </ListItemButton>
            ))}
          </List>
        )}

        {activeTab === 2 && (
          <List sx={{ flex: 1, overflow: "auto", py: 0 }}>
            {history.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: "center" }}>
                No dashboards generated yet
              </Typography>
            )}
            {history.map((h, i) => (
              <ListItemButton
                key={`${h.dashboard_id}-${i}`}
                onClick={() => setDashboard(h)}
              >
                <ListItemText
                  primary={h.title}
                  secondary={`${h.widgets.length} widgets · ${h.generation_time_ms}ms`}
                  slotProps={{
                    primary: { variant: "body2" as const },
                    secondary: { variant: "caption" as const },
                  }}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Box>

      {/* Center: Dashboard Preview */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "auto" }}>
        <Box sx={{ p: 1, display: "flex", alignItems: "center", borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            {dashboard?.title || "Dashboard Preview"}
          </Typography>
          {dashboard?.dashboard_id && (
            <Tooltip title="Dashboard saved">
              <IconButton size="small">
                <SaveIcon fontSize="small" color="success" />
              </IconButton>
            </Tooltip>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ m: 1 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {!dashboard && !loading && (
          <Box sx={{ textAlign: "center", mt: 8, color: "text.secondary" }}>
            <BarChartIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
            <Typography variant="h5" gutterBottom>
              AI Dashboard Generator
            </Typography>
            <Typography variant="body2">
              Describe a dashboard in natural language and the AI will generate it automatically.
            </Typography>
            <Box sx={{ mt: 3, display: "flex", justifyContent: "center", gap: 1, flexWrap: "wrap" }}>
              {["Create a sales dashboard", "Build an HR dashboard", "Show customer churn KPIs"].map((q) => (
                <Chip
                  key={q}
                  label={q}
                  variant="outlined"
                  onClick={() => {
                    setPrompt(q);
                    setActiveTab(0);
                  }}
                  sx={{ cursor: "pointer" }}
                />
              ))}
            </Box>
          </Box>
        )}

        {loading && (
          <Box sx={{ textAlign: "center", mt: 8 }}>
            <CircularProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Planning dashboard, generating SQL, validating...
            </Typography>
          </Box>
        )}

        {dashboard && !loading && (
          <Box sx={{ p: 2 }}>
            {dashboard.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {dashboard.description}
              </Typography>
            )}

            {dashboard.filters && dashboard.filters.length > 0 && (
              <Box sx={{ mb: 2, display: "flex", gap: 1, flexWrap: "wrap" }}>
                {dashboard.filters.map((f: any, i: number) => (
                  <Chip key={i} label={f.label || f.type} size="small" variant="outlined" />
                ))}
              </Box>
            )}

            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 2 }}>
              {dashboard.widgets.map((w) => (
                <WidgetCard
                  key={w.id}
                  widget={w}
                  selected={selectedWidget?.id === w.id}
                  onSelect={() => setSelectedWidget(w)}
                  onExplain={() => handleExplain(w.id)}
                  explanation={explanations[w.id]}
                />
              ))}
            </Box>

            {dashboard.generation_time_ms > 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
                Generated in {dashboard.generation_time_ms}ms
              </Typography>
            )}
          </Box>
        )}
      </Box>

      {/* Right Panel: Widget Properties */}
      <Box
        sx={{
          width: 280,
          flexShrink: 0,
          borderLeft: 1,
          borderColor: "divider",
          height: "100%",
          overflow: "auto",
        }}
      >
        <Box sx={{ p: 1.5, borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Widget Properties
          </Typography>
        </Box>
        <WidgetProperties
          widget={selectedWidget}
          explanation={selectedWidget ? explanations[selectedWidget.id] : undefined}
        />
      </Box>
    </Box>
  );
}
