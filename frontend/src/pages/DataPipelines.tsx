/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import DeleteIcon from "@mui/icons-material/Delete";
import RefreshIcon from "@mui/icons-material/Refresh";
import { rget, rpost, rdel } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Pipeline {
  id: string;
  name: string;
  description: string;
  dataset_id: string;
  steps: any[];
  status: string;
  schedule: string | null;
  last_run: string | null;
  run_count: number;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function DataPipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchPipelines = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ pipelines: Pipeline[]; count: number }>("/ai/de/pipelines");
      setPipelines(res.pipelines || []);
    } catch (e: any) {
      setError(e.message || "Failed to load pipelines");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  const handleRun = async (pipelineId: string) => {
    try {
      await rpost("/ai/de/pipelines/run", { pipeline_id: pipelineId });
      await fetchPipelines();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (pipelineId: string) => {
    if (!confirm("Delete this pipeline?")) return;
    try {
      await rdel(`/ai/de/pipelines/${pipelineId}`);
      await fetchPipelines();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const statusColor: Record<string, "default" | "success" | "warning" | "error"> = {
    draft: "default",
    active: "success",
    paused: "warning",
    failed: "error",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Pipeline Manager
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Save, schedule, and run transformation pipelines
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">Pipelines ({pipelines.length})</Typography>
        <IconButton onClick={fetchPipelines} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : pipelines.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">
            No pipelines yet. Create one from the Transformation Builder.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell align="center">Steps</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Schedule</TableCell>
                <TableCell align="right">Runs</TableCell>
                <TableCell>Last Run</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pipelines.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {p.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {p.description || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip label={p.steps.length} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={p.status}
                      size="small"
                      color={statusColor[p.status] || "default"}
                    />
                  </TableCell>
                  <TableCell>
                    {p.schedule ? (
                      <Chip label={p.schedule} size="small" variant="outlined" />
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell align="right">{p.run_count}</TableCell>
                  <TableCell>
                    {p.last_run
                      ? new Date(p.last_run).toLocaleString()
                      : "-"}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton
                      size="small"
                      onClick={() => handleRun(p.id)}
                      title="Run now"
                    >
                      <PlayArrowIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(p.id)}
                      title="Delete"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
