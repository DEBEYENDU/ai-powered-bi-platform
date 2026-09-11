/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import { rget } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AgentStatusData {
  agent_type: string;
  name: string;
  status: string;
  tasks_completed: number;
  tasks_failed: number;
  avg_duration_ms: number;
  last_active: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function StatusIcon({ status }: { status: string }) {
  if (status === "ready") return <CheckCircleIcon sx={{ color: "success.main" }} />;
  if (status === "busy") return <HourglassEmptyIcon sx={{ color: "warning.main" }} />;
  return <ErrorIcon sx={{ color: "error.main" }} />;
}

function MetricBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <LinearProgress
        variant="determinate"
        value={Math.min(pct, 100)}
        sx={{ flex: 1, height: 8, borderRadius: 4, bgcolor: "grey.200", "& .MuiLinearProgress-bar": { bgcolor: color, borderRadius: 4 } }}
      />
      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 40, textAlign: "right" }}>
        {value}
      </Typography>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function AgentStatus() {
  const [agents, setAgents] = useState<AgentStatusData[]>([]);
  const [error, setError] = useState("");

  const loadAgents = useCallback(() => {
    rget<{ agents: AgentStatusData[] }>("/ai/agents/agents")
      .then((res) => setAgents(res.agents || []))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadAgents();
    const interval = setInterval(loadAgents, 10000);
    return () => clearInterval(interval);
  }, [loadAgents]);

  const maxCompleted = Math.max(...agents.map((a) => a.tasks_completed), 1);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Agent Status</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Real-time status and performance metrics for all registered agents
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "primary.main" }}>
                {agents.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">Total Agents</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "success.main" }}>
                {agents.filter((a) => a.status === "ready").length}
              </Typography>
              <Typography variant="body2" color="text.secondary">Ready</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "info.main" }}>
                {agents.reduce((s, a) => s + a.tasks_completed, 0)}
              </Typography>
              <Typography variant="body2" color="text.secondary">Total Tasks</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: agents.some((a) => a.status === "error") ? "error.main" : "success.main" }}>
                {agents.reduce((s, a) => s + a.tasks_failed, 0)}
              </Typography>
              <Typography variant="body2" color="text.secondary">Total Failures</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Agent Cards */}
      <Typography variant="h6" sx={{ mb: 2 }}>Agent Details</Typography>
      <Grid container spacing={2}>
        {agents.map((a) => {
          const successRate = a.tasks_completed + a.tasks_failed > 0
            ? ((a.tasks_completed / (a.tasks_completed + a.tasks_failed)) * 100).toFixed(1)
            : "0";
          return (
            <Grid key={a.agent_type} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                    <StatusIcon status={a.status} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>{a.name}</Typography>
                    <Chip label={a.agent_type} size="small" variant="outlined" />
                  </Box>

                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">Tasks Completed</Typography>
                    </Box>
                    <MetricBar value={a.tasks_completed} max={maxCompleted} color="#4caf50" />
                  </Box>

                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">Tasks Failed</Typography>
                    </Box>
                    <MetricBar value={a.tasks_failed} max={maxCompleted} color="#f44336" />
                  </Box>

                  <Box sx={{ display: "flex", justifyContent: "space-between", mt: 1 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Success Rate</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{successRate}%</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Avg Duration</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{a.avg_duration_ms.toFixed(0)}ms</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Last Active</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: 12 }}>
                        {a.last_active ? new Date(a.last_active).toLocaleTimeString() : "Never"}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
        {agents.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Paper sx={{ p: 3, textAlign: "center" }}>
              <Typography color="text.secondary">No agents registered</Typography>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
