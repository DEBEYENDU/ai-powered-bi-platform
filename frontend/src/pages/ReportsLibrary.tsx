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
  Dialog,
  DialogContent,
  DialogTitle,
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
import DownloadIcon from "@mui/icons-material/Download";
import DeleteIcon from "@mui/icons-material/Delete";
import HistoryIcon from "@mui/icons-material/History";
import SendIcon from "@mui/icons-material/Send";
import DescriptionIcon from "@mui/icons-material/Description";
import TableChartIcon from "@mui/icons-material/TableChart";
import BarChartIcon from "@mui/icons-material/BarChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import AssessmentIcon from "@mui/icons-material/Assessment";
import ChatIcon from "@mui/icons-material/Chat";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CloseIcon from "@mui/icons-material/Close";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { rget, rpost, rdel } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ReportSection {
  id: string;
  title: string;
  content: string;
  section_type: string;
  data: any;
  order: number;
}

interface ReportKPI {
  name: string;
  value: number | string;
  unit: string;
  change_pct: number;
  trend: string;
  target: number | null;
  description: string;
}

interface ReportInsight {
  title: string;
  description: string;
  insight_type: string;
  metric: string;
  change_pct: number;
  confidence: string;
}

interface ReportRisk {
  title: string;
  description: string;
  severity: string;
  likelihood: string;
  mitigation: string;
}

interface ReportRecommendation {
  title: string;
  description: string;
  priority: string;
  category: string;
  expected_impact: string;
  confidence: string;
}

interface DownloadUrl {
  format: string;
  url: string;
  file_size: number;
}

interface GenerateResult {
  success: boolean;
  report_id: string | null;
  title: string;
  status: string;
  report_type: string;
  sections: ReportSection[];
  kpis: ReportKPI[];
  insights: ReportInsight[];
  risks: ReportRisk[];
  recommendations: ReportRecommendation[];
  executive_summary: string;
  download_urls: DownloadUrl[];
  versions: any[];
  generation_time_ms: number;
  error: string | null;
}

interface ReportListItem {
  id: string;
  title: string;
  report_type: string;
  status: string;
  executive_summary: string;
  generation_time_ms: number;
  created_at: string;
  tags: string[];
}

interface TemplateItem {
  id: string;
  name: string;
  description: string;
  sections: string[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const typeIcon = (type: string) => {
  if (type.includes("sales")) return <TrendingUpIcon sx={{ fontSize: 18, color: "success.main" }} />;
  if (type.includes("finance")) return <AssessmentIcon sx={{ fontSize: 18, color: "primary.main" }} />;
  if (type.includes("marketing")) return <BarChartIcon sx={{ fontSize: 18, color: "warning.main" }} />;
  return <DescriptionIcon sx={{ fontSize: 18, color: "info.main" }} />;
};

const priorityColor = (p: string) => {
  if (p === "critical" || p === "high") return "error";
  if (p === "medium") return "warning";
  return "info";
};

const confidenceColor = (c: string) => {
  if (c === "high") return "success";
  if (c === "medium") return "warning";
  return "error";
};

const REPORT_TYPES = [
  { id: "executive", label: "Executive Report" },
  { id: "sales", label: "Sales Report" },
  { id: "marketing", label: "Marketing Report" },
  { id: "finance", label: "Finance Report" },
  { id: "operations", label: "Operations Report" },
  { id: "customer", label: "Customer Report" },
  { id: "inventory", label: "Inventory Report" },
  { id: "hr", label: "HR Report" },
  { id: "manufacturing", label: "Manufacturing Report" },
  { id: "healthcare", label: "Healthcare Report" },
  { id: "retail", label: "Retail Report" },
  { id: "custom", label: "Custom Report" },
];

/* ------------------------------------------------------------------ */
/*  Report Detail Dialog                                               */
/* ------------------------------------------------------------------ */

function ReportDetailDialog({
  report,
  onClose,
}: {
  report: GenerateResult;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState(0);
  const [followUp, setFollowUp] = useState("");
  const [followUpResult, setFollowUpResult] = useState<string | null>(null);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  const handleFollowUp = useCallback(async () => {
    if (!followUp.trim() || !report.report_id) return;
    setFollowUpLoading(true);
    try {
      const res = await rpost<{ answer: string }>("/ai/reports/followup", {
        report_id: report.report_id,
        question: followUp.trim(),
      });
      setFollowUpResult(res.answer);
      setFollowUp("");
    } catch {
      setFollowUpResult("Failed to get answer.");
    } finally {
      setFollowUpLoading(false);
    }
  }, [followUp, report.report_id]);

  return (
    <Dialog fullScreen open onClose={onClose}>
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        {typeIcon(report.report_type)}
        <Box sx={{ flexGrow: 1 }}>{report.title}</Box>
        <Chip label={report.status} size="small" color={report.status === "completed" ? "success" : "default"} />
        <IconButton onClick={onClose}><CloseIcon /></IconButton>
      </DialogTitle>
      <DialogContent sx={{ p: 0 }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="scrollable" sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tab label="Summary" />
          <Tab label={`Sections (${report.sections.length})`} />
          <Tab label={`KPIs (${report.kpis.length})`} />
          <Tab label={`Insights (${report.insights.length})`} />
          <Tab label={`Risks (${report.risks.length})`} />
          <Tab label={`Recommendations (${report.recommendations.length})`} />
          <Tab label="Downloads" />
          <Tab label="Follow-up" />
        </Tabs>

        <Box sx={{ p: 3, maxHeight: "calc(100vh - 140px)", overflow: "auto" }}>
          {activeTab === 0 && (
            <Box>
              <Typography variant="h6" gutterBottom>Executive Summary</Typography>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.executive_summary}</ReactMarkdown>
            </Box>
          )}

          {activeTab === 1 && (
            <Box>
              {report.sections.map((s, i) => (
                <Card key={i} variant="outlined" sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>{s.title}</Typography>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{s.content}</ReactMarkdown>
                  </CardContent>
                </Card>
              ))}
              {report.sections.length === 0 && <Typography color="text.secondary">No sections generated.</Typography>}
            </Box>
          )}

          {activeTab === 2 && (
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: 2 }}>
              {report.kpis.map((k, i) => (
                <Card key={i} variant="outlined">
                  <CardContent>
                    <Typography variant="caption" color="text.secondary">{k.name}</Typography>
                    <Typography variant="h5" sx={{ fontWeight: 700 }}>
                      {k.value}{k.unit && <Typography component="span" variant="body2"> {k.unit}</Typography>}
                    </Typography>
                    {k.change_pct !== 0 && (
                      <Chip
                        label={`${k.change_pct > 0 ? "+" : ""}${k.change_pct.toFixed(1)}%`}
                        size="small"
                        color={k.change_pct > 0 ? "success" : "error"}
                        sx={{ mt: 0.5 }}
                      />
                    )}
                    {k.description && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                        {k.description}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              ))}
              {report.kpis.length === 0 && <Typography color="text.secondary">No KPIs generated.</Typography>}
            </Box>
          )}

          {activeTab === 3 && (
            <Box>
              {report.insights.map((ins, i) => (
                <Card key={i} variant="outlined" sx={{ mb: 1.5 }}>
                  <CardContent sx={{ py: 1.5 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>{ins.title}</Typography>
                      <Chip label={ins.confidence} size="small" color={confidenceColor(ins.confidence) as any} />
                      {ins.change_pct !== 0 && (
                        <Chip label={`${ins.change_pct > 0 ? "+" : ""}${ins.change_pct.toFixed(1)}%`} size="small" />
                      )}
                    </Box>
                    <Typography variant="body2" color="text.secondary">{ins.description}</Typography>
                  </CardContent>
                </Card>
              ))}
              {report.insights.length === 0 && <Typography color="text.secondary">No insights generated.</Typography>}
            </Box>
          )}

          {activeTab === 4 && (
            <Box>
              {report.risks.map((r, i) => (
                <Card key={i} variant="outlined" sx={{ mb: 1.5, borderLeft: 4, borderColor: r.severity === "high" ? "error.main" : "warning.main" }}>
                  <CardContent>
                    <Box sx={{ display: "flex", gap: 1, mb: 0.5 }}>
                      <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>{r.title}</Typography>
                      <Chip label={r.severity} size="small" color={r.severity === "high" ? "error" : "warning"} />
                    </Box>
                    <Typography variant="body2" color="text.secondary">{r.description}</Typography>
                    {r.mitigation && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                        Mitigation: {r.mitigation}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              ))}
              {report.risks.length === 0 && <Typography color="text.secondary">No risks identified.</Typography>}
            </Box>
          )}

          {activeTab === 5 && (
            <Box>
              {report.recommendations.map((r, i) => (
                <Card key={i} variant="outlined" sx={{ mb: 1.5 }}>
                  <CardContent>
                    <Box sx={{ display: "flex", gap: 1, mb: 0.5 }}>
                      <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>{r.title}</Typography>
                      <Chip label={r.priority} size="small" color={priorityColor(r.priority) as any} />
                      <Chip label={r.category} size="small" variant="outlined" />
                    </Box>
                    <Typography variant="body2" color="text.secondary">{r.description}</Typography>
                    {r.expected_impact && (
                      <Alert severity="success" sx={{ mt: 1, py: 0, fontSize: "0.75rem" }}>
                        Expected impact: {r.expected_impact}
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              ))}
              {report.recommendations.length === 0 && <Typography color="text.secondary">No recommendations.</Typography>}
            </Box>
          )}

          {activeTab === 6 && (
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>Download Reports</Typography>
              {report.download_urls.map((d, i) => (
                <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1.5 }}>
                  <Chip label={d.format.toUpperCase()} size="small" color="primary" />
                  {d.url ? (
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<DownloadIcon />}
                      href={d.url}
                      download
                    >
                      Download {d.format.toUpperCase()}
                    </Button>
                  ) : (
                    <Typography variant="body2" color="text.secondary">Not available</Typography>
                  )}
                  {d.file_size > 0 && (
                    <Typography variant="caption" color="text.secondary">
                      ({(d.file_size / 1024).toFixed(1)} KB)
                    </Typography>
                  )}
                </Box>
              ))}
              {report.download_urls.length === 0 && (
                <Typography color="text.secondary">No downloads available.</Typography>
              )}
            </Box>
          )}

          {activeTab === 7 && (
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Ask about this report</Typography>
              <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
                <TextField
                  fullWidth size="small"
                  placeholder='e.g. "Why did revenue decrease?"'
                  value={followUp}
                  onChange={(e) => setFollowUp(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleFollowUp(); }}
                  disabled={followUpLoading}
                />
                <Button variant="contained" onClick={handleFollowUp} disabled={!followUp.trim() || followUpLoading}
                  startIcon={followUpLoading ? <CircularProgress size={16} /> : <SendIcon />}>
                  Ask
                </Button>
              </Box>
              {followUpResult && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{followUpResult}</ReactMarkdown>
                </Alert>
              )}
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {["Summarize this report", "What are the top risks?", "Compare with last quarter"].map((q) => (
                  <Chip key={q} label={q} size="small" variant="outlined" onClick={() => setFollowUp(q)} sx={{ cursor: "pointer" }} />
                ))}
              </Box>
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  Main ReportsLibrary Page                                           */
/* ------------------------------------------------------------------ */

export function ReportsLibrary() {
  const [prompt, setPrompt] = useState("");
  const [reportType, setReportType] = useState("custom");
  const [formats, setFormats] = useState<string[]>(["pdf"]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [detailReport, setDetailReport] = useState<GenerateResult | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    rget<{ reports: ReportListItem[] }>("/ai/reports?page_size=50").then((res) => setReports(res.reports || [])).catch(() => {});
    rget<TemplateItem[]>("/ai/reports/templates/list").then(setTemplates).catch(() => {});
  }, []);

  const handleGenerate = useCallback(async () => {
    const q = prompt.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    setPrompt("");
    try {
      const res = await rpost<GenerateResult>("/ai/reports/generate", {
        prompt: q,
        report_type: reportType,
        formats,
      });
      setResult(res);
      if (res.success && res.report_id) {
        setReports((prev) => [{
          id: res.report_id!,
          title: res.title,
          report_type: res.report_type,
          status: res.status,
          executive_summary: res.executive_summary.slice(0, 200),
          generation_time_ms: res.generation_time_ms,
          created_at: new Date().toISOString(),
          tags: [],
        }, ...prev]);
      }
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [prompt, reportType, formats, loading]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await rdel(`/ai/reports/${id}`);
      setReports((prev) => prev.filter((r) => r.id !== id));
    } catch { /* ignore */ }
  }, []);

  const filteredReports = reports.filter((r) =>
    !search || r.title.toLowerCase().includes(search.toLowerCase()) || r.report_type.includes(search.toLowerCase())
  );

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 64px - 48px)" }}>
      {/* Left Panel: Generate + Templates + History */}
      <Box sx={{ width: 340, flexShrink: 0, display: "flex", flexDirection: "column", borderRight: 1, borderColor: "divider", height: "100%" }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="fullWidth">
          <Tab icon={<AddIcon />} iconPosition="start" label="Generate" sx={{ minHeight: 40 }} />
          <Tab icon={<DescriptionIcon />} iconPosition="start" label="Templates" sx={{ minHeight: 40 }} />
          <Tab icon={<HistoryIcon />} iconPosition="start" label="History" sx={{ minHeight: 40 }} />
        </Tabs>
        <Divider />

        {activeTab === 0 && (
          <Box sx={{ p: 1.5, flex: 1, overflow: "auto" }}>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Describe your report
            </Typography>
            <TextField
              multiline maxRows={6}
              placeholder="e.g. Generate Q2 Sales Report with revenue trends and recommendations"
              value={prompt} onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleGenerate(); } }}
              fullWidth size="small" disabled={loading} sx={{ mt: 0.5, mb: 1 }}
            />
            <TextField
              select fullWidth size="small" label="Report Type" value={reportType}
              onChange={(e) => setReportType(e.target.value)} sx={{ mb: 1 }}
              slotProps={{ inputLabel: { shrink: true } }}
            >
              {REPORT_TYPES.map((t) => (
                <MenuItem key={t.id} value={t.id}>{t.label}</MenuItem>
              ))}
            </TextField>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>Export Formats</Typography>
            <Box sx={{ display: "flex", gap: 0.5, mb: 1, flexWrap: "wrap" }}>
              {["pdf", "docx", "pptx", "xlsx", "csv", "json", "markdown", "html"].map((f) => (
                <Chip
                  key={f} label={f.toUpperCase()} size="small"
                  color={formats.includes(f) ? "primary" : "default"}
                  variant={formats.includes(f) ? "filled" : "outlined"}
                  onClick={() => setFormats((prev) => prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f])}
                  sx={{ cursor: "pointer" }}
                />
              ))}
            </Box>
            <Button
              variant="contained" fullWidth onClick={handleGenerate}
              disabled={!prompt.trim() || loading}
              startIcon={loading ? <CircularProgress size={16} /> : <AutoAwesomeIcon />}
            >
              {loading ? "Generating..." : "Generate Report"}
            </Button>
          </Box>
        )}

        {activeTab === 1 && (
          <List sx={{ flex: 1, overflow: "auto", py: 0 }}>
            {templates.map((t) => (
              <ListItemButton key={t.id} onClick={() => { setPrompt(`Generate a ${t.name}`); setReportType(t.id); setActiveTab(0); }}>
                <ListItemText
                  primary={t.name}
                  secondary={t.description}
                  slotProps={{ primary: { variant: "body2" as const }, secondary: { variant: "caption" as const } }}
                />
              </ListItemButton>
            ))}
          </List>
        )}

        {activeTab === 2 && (
          <Box sx={{ flex: 1, overflow: "auto" }}>
            <TextField
              fullWidth size="small" placeholder="Search reports..."
              value={search} onChange={(e) => setSearch(e.target.value)}
              sx={{ p: 1, pb: 0 }}
            />
            <List sx={{ py: 0 }}>
              {filteredReports.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: "center" }}>
                  No reports yet
                </Typography>
              )}
              {filteredReports.map((r) => (
                <ListItemButton key={r.id} onClick={() => {
                  rget<GenerateResult>(`/ai/reports/${r.id}`).then(setDetailReport).catch(() => {});
                }}>
                  <ListItemText
                    primary={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                        {typeIcon(r.report_type)}
                        <Typography variant="body2" noWrap sx={{ flexGrow: 1 }}>{r.title}</Typography>
                      </Box>
                    }
                    secondary={`${r.report_type} · ${r.generation_time_ms?.toFixed(0) || 0}ms`}
                    slotProps={{ primary: { noWrap: true }, secondary: { variant: "caption" as const } }}
                  />
                  <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleDelete(r.id); }}>
                    <DeleteIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </ListItemButton>
              ))}
            </List>
          </Box>
        )}
      </Box>

      {/* Center: Preview / Empty State */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "auto" }}>
        <Box sx={{ p: 1, display: "flex", alignItems: "center", borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            {result?.title || "AI Report Generator"}
          </Typography>
          {result?.report_id && (
            <Button size="small" onClick={() => setDetailReport(result)}>
              View Full Report
            </Button>
          )}
        </Box>

        {error && <Alert severity="error" sx={{ m: 1 }} onClose={() => setError(null)}>{error}</Alert>}

        {!result && !loading && (
          <Box sx={{ textAlign: "center", mt: 8, color: "text.secondary" }}>
            <DescriptionIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
            <Typography variant="h5" gutterBottom>AI Report Generator</Typography>
            <Typography variant="body2">
              Generate professional business reports from natural language descriptions.
            </Typography>
            <Box sx={{ mt: 3, display: "flex", justifyContent: "center", gap: 1, flexWrap: "wrap" }}>
              {["Generate a quarterly sales report", "Create an executive summary", "Generate HR report", "Create a customer churn analysis"].map((q) => (
                <Chip key={q} label={q} variant="outlined" onClick={() => { setPrompt(q); setActiveTab(0); }} sx={{ cursor: "pointer" }} />
              ))}
            </Box>
          </Box>
        )}

        {loading && (
          <Box sx={{ textAlign: "center", mt: 8 }}>
            <CircularProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Loading data, generating content, creating exports...
            </Typography>
          </Box>
        )}

        {result && !loading && (
          <Box sx={{ p: 2 }}>
            {result.executive_summary && (
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Executive Summary</Typography>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.executive_summary}</ReactMarkdown>
                </CardContent>
              </Card>
            )}

            {result.kpis.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Key Metrics</Typography>
                <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 1.5 }}>
                  {result.kpis.slice(0, 8).map((k, i) => (
                    <Card key={i} variant="outlined">
                      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                        <Typography variant="caption" color="text.secondary">{k.name}</Typography>
                        <Typography variant="h6" sx={{ fontWeight: 700 }}>
                          {k.value}{k.unit ? ` ${k.unit}` : ""}
                        </Typography>
                        {k.change_pct !== 0 && (
                          <Chip label={`${k.change_pct > 0 ? "+" : ""}${k.change_pct.toFixed(1)}%`} size="small"
                            color={k.change_pct > 0 ? "success" : "error"} />
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              </Box>
            )}

            {result.sections.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Report Sections</Typography>
                {result.sections.slice(0, 5).map((s, i) => (
                  <Card key={i} variant="outlined" sx={{ mb: 1 }}>
                    <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                      <Typography variant="subtitle2">{s.title}</Typography>
                      <Typography variant="body2" color="text.secondary" noWrap>{s.content.slice(0, 150)}...</Typography>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}

            {result.download_urls.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Downloads</Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                  {result.download_urls.map((d, i) => (
                    <Button key={i} variant="outlined" size="small" startIcon={<DownloadIcon />}
                      href={d.url} download disabled={!d.url}>
                      {d.format.toUpperCase()}
                    </Button>
                  ))}
                </Box>
              </Box>
            )}

            <Typography variant="caption" color="text.secondary">
              Generated in {result.generation_time_ms?.toFixed(0) || 0}ms
            </Typography>
          </Box>
        )}
      </Box>

      {/* Detail Dialog */}
      {detailReport && (
        <ReportDetailDialog report={detailReport} onClose={() => setDetailReport(null)} />
      )}
    </Box>
  );
}
