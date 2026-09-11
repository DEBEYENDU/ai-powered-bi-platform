/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { rget } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AgentLog {
  id: string;
  timestamp: string;
  level: string;
  agent_type: string;
  task_id: string;
  message: string;
  data: Record<string, any>;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function LevelChip({ level }: { level: string }) {
  const color: Record<string, "error" | "warning" | "info" | "success" | "default"> = {
    error: "error",
    warning: "warning",
    info: "info",
    debug: "default",
  };
  return <Chip label={level} color={color[level] || "default"} size="small" variant="outlined" />;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function AgentLogs() {
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [error, setError] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");

  const loadLogs = useCallback(() => {
    const params = new URLSearchParams();
    if (levelFilter) params.set("level", levelFilter);
    if (agentFilter) params.set("agent_type", agentFilter);
    params.set("limit", "200");

    rget<{ logs: AgentLog[] }>(`/ai/agents/logs?${params.toString()}`)
      .then((res) => setLogs(res.logs || []))
      .catch((e) => setError(e.message));
  }, [levelFilter, agentFilter]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const agentTypes = [...new Set(logs.map((l) => l.agent_type).filter(Boolean))];

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Agent Logs</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Real-time log stream from all multi-agent executions
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Log Level</InputLabel>
              <Select value={levelFilter} label="Log Level" onChange={(e) => setLevelFilter(e.target.value)}>
                <MenuItem value="">All Levels</MenuItem>
                <MenuItem value="info">Info</MenuItem>
                <MenuItem value="warning">Warning</MenuItem>
                <MenuItem value="error">Error</MenuItem>
                <MenuItem value="debug">Debug</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Agent Type</InputLabel>
              <Select value={agentFilter} label="Agent Type" onChange={(e) => setAgentFilter(e.target.value)}>
                <MenuItem value="">All Agents</MenuItem>
                {agentTypes.map((at) => (
                  <MenuItem key={at} value={at}>{at}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Typography variant="body2" color="text.secondary">
              {logs.length} log entries
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Log Table */}
      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Timestamp</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Level</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Agent</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Task ID</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Message</Typography></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary" sx={{ py: 3 }}>No logs available</Typography>
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id} hover sx={{ bgcolor: log.level === "error" ? "error.50" : undefined }}>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                      {log.timestamp}
                    </Typography>
                  </TableCell>
                  <TableCell><LevelChip level={log.level} /></TableCell>
                  <TableCell>
                    <Chip label={log.agent_type || "system"} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                      {log.task_id || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {log.message}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
