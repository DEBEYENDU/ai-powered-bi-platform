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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import ScheduleIcon from "@mui/icons-material/Schedule";
import { rget, rpost, rdel } from "../api";

interface Workflow {
  id: string; name: string; description: string; status: string;
  tags: string[]; last_run_at: string | null; next_run_at: string | null; created_at: string;
}

const statusColor: Record<string, "success" | "warning" | "error" | "info" | "default"> = {
  active: "success", paused: "warning", failed: "error", draft: "default", completed: "info", disabled: "default",
};

export function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    rget<{ workflows: Workflow[] }>("/workflows?limit=100")
      .then((res) => setWorkflows(res.workflows || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleActivate = async (id: string) => {
    try {
      await rpost(`/workflows/${id}/activate`);
      setSuccess("Workflow activated");
      load();
    } catch (e: any) { setError(e.message); }
  };

  const handlePause = async (id: string) => {
    try {
      await rpost(`/workflows/${id}/pause`);
      setSuccess("Workflow paused");
      load();
    } catch (e: any) { setError(e.message); }
  };

  const handleRun = async (id: string) => {
    try {
      await rpost(`/workflows/${id}/run`, { input_data: {} });
      setSuccess("Workflow execution started");
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async (id: string) => {
    try {
      await rdel(`/workflows/${id}`);
      setSuccess("Workflow deleted");
      load();
    } catch (e: any) { setError(e.message); }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>Workflows</Typography>
          <Typography variant="body2" color="text.secondary">Create and manage automated BI workflows</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => window.location.href = "/workflows/builder"}>
          New Workflow
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: "Total", value: workflows.length, color: "primary.main" },
          { label: "Active", value: workflows.filter(w => w.status === "active").length, color: "success.main" },
          { label: "Paused", value: workflows.filter(w => w.status === "paused").length, color: "warning.main" },
          { label: "Draft", value: workflows.filter(w => w.status === "draft").length, color: "grey.500" },
        ].map((s) => (
          <Grid key={s.label} size={{ xs: 6, md: 3 }}>
            <Card><CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: s.color }}>{s.value}</Typography>
              <Typography variant="body2" color="text.secondary">{s.label}</Typography>
            </CardContent></Card>
          </Grid>
        ))}
      </Grid>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}><CircularProgress /></Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Name</Typography></TableCell>
                <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Status</Typography></TableCell>
                <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Tags</Typography></TableCell>
                <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Last Run</Typography></TableCell>
                <TableCell><Typography variant="caption" sx={{ fontWeight: 700 }}>Next Run</Typography></TableCell>
                <TableCell align="right"><Typography variant="caption" sx={{ fontWeight: 700 }}>Actions</Typography></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {workflows.length === 0 ? (
                <TableRow><TableCell colSpan={6} align="center">
                  <Typography color="text.secondary" sx={{ py: 3 }}>No workflows yet. Create your first workflow!</Typography>
                </TableCell></TableRow>
              ) : workflows.map((wf) => (
                <TableRow key={wf.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>{wf.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{wf.description?.slice(0, 60)}</Typography>
                  </TableCell>
                  <TableCell><Chip label={wf.status} color={statusColor[wf.status] || "default"} size="small" /></TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {wf.tags?.slice(0, 3).map((t) => <Chip key={t} label={t} size="small" variant="outlined" />)}
                    </Box>
                  </TableCell>
                  <TableCell><Typography variant="caption" color="text.secondary">{wf.last_run_at || "Never"}</Typography></TableCell>
                  <TableCell><Typography variant="caption" color="text.secondary">{wf.next_run_at || "-"}</Typography></TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: "flex", gap: 0.5, justifyContent: "flex-end" }}>
                      <Button size="small" onClick={() => handleRun(wf.id)} startIcon={<PlayArrowIcon />}>Run</Button>
                      {wf.status === "active" ? (
                        <Button size="small" onClick={() => handlePause(wf.id)} startIcon={<PauseIcon />}>Pause</Button>
                      ) : (
                        <Button size="small" onClick={() => handleActivate(wf.id)} startIcon={<CheckCircleIcon />}>Activate</Button>
                      )}
                      <Button size="small" color="error" onClick={() => handleDelete(wf.id)}>Delete</Button>
                    </Box>
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
