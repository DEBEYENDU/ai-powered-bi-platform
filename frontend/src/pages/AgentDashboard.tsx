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
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import SendIcon from "@mui/icons-material/Send";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AgentStatus {
  agent_type: string;
  name: string;
  status: string;
  tasks_completed: number;
  tasks_failed: number;
  avg_duration_ms: number;
  last_active: string;
}

interface TaskStep {
  step_id: string;
  agent_type: string;
  description: string;
  status: string;
  duration_ms: number;
  error: string | null;
}

interface AgentRunResult {
  success: boolean;
  task_id: string;
  answer: string;
  agent_sequence: string[];
  steps: TaskStep[];
  metrics: {
    total_duration_ms: number;
    agents_called: number;
    failures: number;
    retries: number;
  };
  artifacts: any[];
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function StatusChip({ status }: { status: string }) {
  const color: Record<string, "success" | "warning" | "error" | "default" | "info"> = {
    ready: "success",
    busy: "warning",
    error: "error",
    completed: "success",
    failed: "error",
    running: "info",
    pending: "default",
  };
  return <Chip label={status} color={color[status] || "default"} size="small" />;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function AgentDashboard() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [task, setTask] = useState("");
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [taskHistory, setTaskHistory] = useState<any[]>([]);

  const loadAgents = useCallback(() => {
    rget<{ agents: AgentStatus[] }>("/ai/agents/agents")
      .then((res) => setAgents(res.agents || []))
      .catch((e) => setError(e.message));
  }, []);

  const loadHistory = useCallback(() => {
    rget<{ tasks: any[] }>("/ai/agents/tasks?limit=10")
      .then((res) => setTaskHistory(res.tasks || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadAgents();
    loadHistory();
  }, [loadAgents, loadHistory]);

  const handleRun = async () => {
    if (!task.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await rpost<AgentRunResult>("/ai/agents/run", {
        task: task.trim(),
        priority: "medium",
        max_retries: 2,
        timeout_seconds: 300,
      });
      setResult(res);
      loadHistory();
    } catch (e: any) {
      setError(e.message || "Agent execution failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Multi-Agent Dashboard</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Orchestrate specialized AI agents to solve complex business intelligence tasks
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Agent Status Cards */}
      <Typography variant="h6" sx={{ mb: 2 }}>Registered Agents</Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {agents.map((a) => (
          <Grid key={a.agent_type} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <SmartToyIcon fontSize="small" color="primary" />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>{a.name}</Typography>
                </Box>
                <StatusChip status={a.status} />
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Tasks: {a.tasks_completed} completed, {a.tasks_failed} failed
                  </Typography>
                  <br />
                  <Typography variant="caption" color="text.secondary">
                    Avg: {a.avg_duration_ms.toFixed(0)}ms
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {agents.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Paper sx={{ p: 3, textAlign: "center" }}>
              <Typography color="text.secondary">No agents registered yet</Typography>
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* Task Input */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Run Agent Task</Typography>
        <Box sx={{ display: "flex", gap: 2, alignItems: "flex-end" }}>
          <TextField
            fullWidth
            multiline
            minRows={2}
            maxRows={4}
            label="Describe your task in natural language"
            placeholder="e.g., Analyze Q3 revenue trends and create a forecast for Q4"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleRun();
              }
            }}
          />
          <Button
            variant="contained"
            onClick={handleRun}
            disabled={!task.trim() || loading}
            startIcon={loading ? <CircularProgress size={18} /> : <SendIcon />}
            sx={{ minWidth: 140, height: 56 }}
          >
            {loading ? "Running..." : "Run"}
          </Button>
        </Box>
      </Paper>

      {/* Results */}
      {result && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Result {result.success ? "✓" : "✗"} — Task {result.task_id}
          </Typography>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid size={{ xs: 6, md: 3 }}>
              <Card><CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">Duration</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {(result.metrics.total_duration_ms / 1000).toFixed(1)}s
                </Typography>
              </CardContent></Card>
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Card><CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">Agents Used</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{result.metrics.agents_called}</Typography>
              </CardContent></Card>
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Card><CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">Failures</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700, color: result.metrics.failures > 0 ? "error.main" : "text.primary" }}>
                  {result.metrics.failures}
                </Typography>
              </CardContent></Card>
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <Card><CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">Retries</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{result.metrics.retries}</Typography>
              </CardContent></Card>
            </Grid>
          </Grid>

          {/* Agent Sequence */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Agent Sequence</Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              {result.agent_sequence.map((a, i) => (
                <Chip key={i} label={a} color="primary" variant="outlined" size="small" />
              ))}
            </Box>
          </Box>

          {/* Steps */}
          <Typography variant="subtitle2" sx={{ mb: 1 }}>Execution Steps</Typography>
          {result.steps.map((step) => (
            <Box key={step.step_id} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5, py: 0.5, borderBottom: "1px solid #eee" }}>
              <StatusChip status={step.status} />
              <Typography variant="body2" sx={{ flex: 1 }}>{step.agent_type}</Typography>
              <Typography variant="caption" color="text.secondary">{step.duration_ms.toFixed(0)}ms</Typography>
              {step.error && <Typography variant="caption" color="error.main">{step.error}</Typography>}
            </Box>
          ))}

          {/* Answer */}
          {result.answer && (
            <Paper sx={{ p: 2, mt: 2, bgcolor: "grey.50" }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Answer</Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{result.answer}</Typography>
            </Paper>
          )}

          {result.error && (
            <Alert severity="error" sx={{ mt: 2 }}>{result.error}</Alert>
          )}
        </Paper>
      )}

      {/* Task History */}
      <Typography variant="h6" sx={{ mb: 2 }}>Recent Tasks</Typography>
      <Paper>
        {taskHistory.length === 0 ? (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography color="text.secondary">No tasks executed yet</Typography>
          </Box>
        ) : (
          <Box>
            {taskHistory.map((t, i) => (
              <Box key={i} sx={{ px: 2, py: 1, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>{t.task}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t.agents_used?.join(" → ")} • {t.completed_at}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">{t.duration_ms?.toFixed(0)}ms</Typography>
              </Box>
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  );
}
