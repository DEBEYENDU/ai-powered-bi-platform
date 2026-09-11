/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Paper,
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

interface TaskRecord {
  task_id: string;
  task: string;
  agent_sequence: string[];
  answer: string;
  duration_ms: number;
  agents_called: number;
  failures: number;
  retries: number;
  completed_at: string;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function TaskHistory() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [error, setError] = useState("");

  const loadTasks = useCallback(() => {
    rget<{ tasks: TaskRecord[] }>("/ai/agents/tasks?limit=100")
      .then((res) => setTasks(res.tasks || []))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Task History</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        View all multi-agent task executions and their results
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Task ID</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Task</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Agent Sequence</Typography></TableCell>
              <TableCell align="right"><Typography variant="caption" sx={{ fontWeight: 700 }}>Duration</Typography></TableCell>
              <TableCell align="right"><Typography variant="caption" sx={{ fontWeight: 700 }}>Agents</Typography></TableCell>
              <TableCell align="right"><Typography variant="caption" sx={{ fontWeight: 700 }}>Failures</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Completed</Typography></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tasks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary" sx={{ py: 3 }}>No task history yet</Typography>
                </TableCell>
              </TableRow>
            ) : (
              tasks.map((t) => (
                <TableRow key={t.task_id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 12 }}>{t.task_id}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {t.task}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {t.agent_sequence?.map((a, i) => (
                        <Chip key={i} label={a} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">{(t.duration_ms / 1000).toFixed(1)}s</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">{t.agents_called}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color={t.failures > 0 ? "error.main" : "text.primary"}>
                      {t.failures}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">{t.completed_at}</Typography>
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
