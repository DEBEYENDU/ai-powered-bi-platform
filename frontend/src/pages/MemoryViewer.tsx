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

interface MemoryEntry {
  id: string;
  memory_type: string;
  key: string;
  value: any;
  agent_type: string;
  task_id: string;
  session_id: string;
  embedding: number[] | null;
  expires_at: string | null;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function MemoryViewer() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [stats, setStats] = useState<Record<string, any>>({});
  const [error, setError] = useState("");

  const loadData = useCallback(() => {
    rget<{ entries: MemoryEntry[] }>("/ai/agents/memory")
      .then((res) => setEntries(res.entries || []))
      .catch((e) => setError(e.message));

    rget<Record<string, any>>("/ai/agents/stats")
      .then((res) => setStats(res.memory_stats || {}))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Memory Viewer</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Inspect conversation, task, and shared memory entries across all agents
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Stats */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Memory Store Statistics</Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {Object.entries(stats).map(([key, val]) => (
            <Chip key={key} label={`${key}: ${val}`} variant="outlined" />
          ))}
          {Object.keys(stats).length === 0 && (
            <Typography variant="body2" color="text.secondary">No stats available</Typography>
          )}
        </Box>
      </Paper>

      {/* Memory Entries */}
      <Typography variant="h6" sx={{ mb: 2 }}>Memory Entries ({entries.length})</Typography>
      <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Type</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Key</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Value</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Agent</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Session</Typography></TableCell>
              <TableCell sx={{ bgcolor: "grey.100" }}><Typography variant="caption" sx={{ fontWeight: 700 }}>Created</Typography></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary" sx={{ py: 3 }}>No memory entries stored yet</Typography>
                </TableCell>
              </TableRow>
            ) : (
              entries.map((entry, i) => (
                <TableRow key={i} hover>
                  <TableCell>
                    <Chip
                      label={entry.memory_type}
                      size="small"
                      color={
                        entry.memory_type === "conversation" ? "primary"
                          : entry.memory_type === "task" ? "secondary"
                          : "default"
                      }
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 12 }}>
                      {entry.key.slice(0, 30)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {typeof entry.value === "string"
                        ? entry.value.slice(0, 100)
                        : JSON.stringify(entry.value).slice(0, 100)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{entry.agent_type || "-"}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace", fontSize: 11 }}>
                      {entry.session_id || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">{entry.created_at}</Typography>
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
