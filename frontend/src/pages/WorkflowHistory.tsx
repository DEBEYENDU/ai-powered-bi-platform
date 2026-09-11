/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box,
  Chip,
  CircularProgress,
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

export function WorkflowHistory() {
  const { id } = useParams<{ id: string }>();
  const [executions, setExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!id) return;
    rget<any>(`/workflows/${id}/executions?limit=100`)
      .then((res) => setExecutions(res.executions || []))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}><CircularProgress /></Box>;

  const statusColor: Record<string, "success" | "error" | "warning" | "info" | "default"> = {
    completed: "success", failed: "error", running: "info", pending: "default",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Execution History</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        View all executions for this workflow
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Execution ID</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Status</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Trigger</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Test</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Duration</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Errors</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Started</Typography></TableCell>
              <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Completed</Typography></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {executions.length === 0 ? (
              <TableRow><TableCell colSpan={8} align="center">
                <Typography color="text.secondary" sx={{ py: 3 }}>No executions yet</Typography>
              </TableCell></TableRow>
            ) : executions.map((e) => (
              <TableRow key={e.id} hover sx={{ bgcolor: e.is_test ? "grey.50" : undefined }}>
                <TableCell><Typography variant="caption" sx={{ fontFamily: "monospace" }}>{e.id}</Typography></TableCell>
                <TableCell><Chip label={e.status} color={statusColor[e.status] || "default"} size="small" /></TableCell>
                <TableCell><Chip label={e.trigger_type} size="small" variant="outlined" /></TableCell>
                <TableCell>{e.is_test ? <Chip label="Test" size="small" color="warning" /> : "-"}</TableCell>
                <TableCell>{(e.duration_ms / 1000).toFixed(1)}s</TableCell>
                <TableCell><Typography variant="body2" color={e.errors?.length ? "error.main" : "text.primary"}>{e.errors?.length || 0}</Typography></TableCell>
                <TableCell><Typography variant="caption" color="text.secondary">{e.started_at}</Typography></TableCell>
                <TableCell><Typography variant="caption" color="text.secondary">{e.completed_at || "-"}</Typography></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
