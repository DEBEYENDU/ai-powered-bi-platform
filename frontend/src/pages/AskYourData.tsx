/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useState } from "react";
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
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import SendIcon from "@mui/icons-material/Send";
import BarChartIcon from "@mui/icons-material/BarChart";
import TableChartIcon from "@mui/icons-material/TableChart";
import ScatterPlotIcon from "@mui/icons-material/ScatterPlot";
import PieChartIcon from "@mui/icons-material/PieChart";
import TimelineIcon from "@mui/icons-material/Timeline";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ChartRecommendation {
  type: string;
  x_axis: string;
  y_axis: string;
  reason: string;
}

interface QueryResult {
  success: boolean;
  question: string;
  sql: string;
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  truncated: boolean;
  execution_time_ms: number;
  explanation: string;
  chart_recommendation: ChartRecommendation | null;
  error: string | null;
}

interface ExplainResult {
  sql: string;
  explanation: string;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const CHART_ICONS: Record<string, any> = {
  bar: BarChartIcon,
  line: TimelineIcon,
  pie: PieChartIcon,
  scatter: ScatterPlotIcon,
  table: TableChartIcon,
};

const EXAMPLE_QUESTIONS = [
  "How many users are in the system?",
  "Show me all dashboards with their owners",
  "What datasets have the most rows?",
  "List all organizations and their user counts",
  "Which users signed up most recently?",
  "Show me the breakdown of datasets by status",
];

function ChartChip({ rec }: { rec: ChartRecommendation }) {
  const Icon = CHART_ICONS[rec.type] || BarChartIcon;
  return (
    <Chip
      icon={<Icon sx={{ fontSize: 16 }} />}
      label={`${rec.type.toUpperCase()} — ${rec.x_axis} vs ${rec.y_axis}`}
      size="small"
      color="primary"
      variant="outlined"
    />
  );
}

function SQLBlock({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);
  const copySql = () => {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <Paper variant="outlined" sx={{ position: "relative" }}>
      <Box sx={{ display: "flex", alignItems: "center", px: 1.5, py: 0.5, borderBottom: 1, borderColor: "divider" }}>
        <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1 }}>
          SQL
        </Typography>
        <Tooltip title={copied ? "Copied!" : "Copy SQL"}>
          <IconButton size="small" onClick={copySql}>
            <ContentCopyIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
      </Box>
      <Box sx={{ p: 2, fontFamily: "monospace", fontSize: "0.85rem", overflowX: "auto" }}>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{sql}</pre>
      </Box>
    </Paper>
  );
}

function ResultTable({ columns, rows }: { columns: string[]; rows: Record<string, any>[] }) {
  if (columns.length === 0 || rows.length === 0) return null;
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 500 }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col} sx={{ fontWeight: 600, fontFamily: "monospace", fontSize: "0.8rem" }}>
                {col}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i} hover>
              {columns.map((col) => (
                <TableCell key={col} sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                  {row[col] === null ? (
                    <Typography component="span" color="text.secondary" sx={{ fontStyle: "italic" }}>
                      NULL
                    </Typography>
                  ) : (
                    String(row[col])
                  )}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Query History Item                                                 */
/* ------------------------------------------------------------------ */

function QueryHistoryItem({ result }: { result: QueryResult }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent sx={{ pb: "16px !important" }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
            {result.question}
          </Typography>
          <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
            {result.success ? (
              <Chip label={`${result.row_count} rows`} size="small" color="success" variant="outlined" />
            ) : (
              <Chip label="Error" size="small" color="error" variant="outlined" />
            )}
            <Chip label={`${result.execution_time_ms}ms`} size="small" variant="outlined" />
            {result.chart_recommendation && <ChartChip rec={result.chart_recommendation} />}
            <IconButton size="small" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>

        {result.error && (
          <Alert severity="error" sx={{ mb: 1 }}>
            {result.error}
          </Alert>
        )}

        {expanded && (
          <>
            <SQLBlock sql={result.sql} />

            {result.explanation && (
              <Box sx={{ mt: 1.5, p: 1.5, bgcolor: "grey.900", borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  EXPLANATION
                </Typography>
                <Box sx={{ "& p": { my: 0.5 } }}>
                  <Markdown remarkPlugins={[remarkGfm]}>{result.explanation}</Markdown>
                </Box>
              </Box>
            )}

            {result.success && result.rows.length > 0 && (
              <Box sx={{ mt: 1.5 }}>
                <ResultTable columns={result.columns} rows={result.rows} />
                {result.truncated && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                    Results truncated (showing first {result.rows.length} rows).
                  </Typography>
                )}
              </Box>
            )}

            {result.chart_recommendation && (
              <Box sx={{ mt: 1.5, p: 1.5, bgcolor: "primary.dark", borderRadius: 1, opacity: 0.9 }}>
                <Typography variant="caption" sx={{ fontWeight: 600 }}>
                  Chart Recommendation
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {result.chart_recommendation.reason}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                  X-axis: {result.chart_recommendation.x_axis} · Y-axis: {result.chart_recommendation.y_axis}
                </Typography>
              </Box>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main AskYourData Page                                              */
/* ------------------------------------------------------------------ */

export function AskYourData() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<QueryResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = useCallback(async () => {
    const q = question.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setQuestion("");

    try {
      const res = await rpost<QueryResult>("/ai/query", { question: q });
      setResults((prev) => [res, ...prev]);
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [question, loading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <Box sx={{ maxWidth: 900, mx: "auto" }}>
      <Typography variant="h4" gutterBottom>
        Ask Your Data
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Ask a question in plain English. The AI will generate SQL, execute it, and show results with
        chart recommendations.
      </Typography>

      {/* Input */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", gap: 1, alignItems: "flex-end" }}>
          <TextField
            multiline
            maxRows={4}
            placeholder="e.g. How many users are in each organization?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            fullWidth
            size="small"
            disabled={loading}
          />
          <Button
            variant="contained"
            onClick={handleAsk}
            disabled={!question.trim() || loading}
            sx={{ minWidth: 44, minHeight: 40 }}
          >
            {loading ? <CircularProgress size={20} /> : <SendIcon />}
          </Button>
        </Box>

        {/* Example questions */}
        {results.length === 0 && !loading && (
          <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {EXAMPLE_QUESTIONS.map((eq) => (
              <Chip
                key={eq}
                label={eq}
                size="small"
                variant="outlined"
                onClick={() => setQuestion(eq)}
                sx={{ cursor: "pointer" }}
              />
            ))}
          </Box>
        )}
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Results */}
      {results.map((r, i) => (
        <QueryHistoryItem key={`${r.question}-${i}`} result={r} />
      ))}

      {loading && results.length === 0 && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Generating SQL and executing query...
          </Typography>
        </Box>
      )}
    </Box>
  );
}
