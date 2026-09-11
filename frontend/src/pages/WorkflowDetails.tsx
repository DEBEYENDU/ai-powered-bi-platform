/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { rget, rpost } from "../api";

export function WorkflowDetails() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => {
    if (!id) return;
    rget<any>(`/workflows/${id}`)
      .then((res) => setWorkflow(res))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleRun = async (test = false) => {
    if (!id) return;
    try {
      await rpost(`/workflows/${id}/${test ? "test" : "run"}`, { input_data: {}, is_test: test });
      setSuccess(test ? "Test execution started" : "Workflow execution started");
    } catch (e: any) { setError(e.message); }
  };

  const handleStatus = async (status: string) => {
    if (!id) return;
    try {
      await rpost(`/workflows/${id}/${status}`);
      setSuccess(`Workflow ${status}d`);
      load();
    } catch (e: any) { setError(e.message); }
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}><CircularProgress /></Box>;
  if (!workflow?.success) return <Alert severity="error">{workflow?.error || "Not found"}</Alert>;

  const w = workflow;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 1 }}>{w.name}</Typography>
          <Typography variant="body2" color="text.secondary">{w.description}</Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Chip label={w.status} color={w.status === "active" ? "success" : w.status === "paused" ? "warning" : "default"} />
          <Button variant="contained" size="small" startIcon={<PlayArrowIcon />} onClick={() => handleRun(false)}>Run</Button>
          <Button variant="outlined" size="small" onClick={() => handleRun(true)}>Test Run</Button>
          {w.status === "active" ? (
            <Button variant="outlined" size="small" startIcon={<PauseIcon />} onClick={() => handleStatus("pause")}>Pause</Button>
          ) : (
            <Button variant="outlined" size="small" startIcon={<CheckCircleIcon />} onClick={() => handleStatus("activate")}>Activate</Button>
          )}
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* Trigger */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Trigger</Typography>
            <Chip label={w.trigger?.type || "manual"} color="info" sx={{ mb: 1 }} />
            {w.trigger?.time && <Typography variant="body2">Time: {w.trigger.time}</Typography>}
            {w.trigger?.day_of_week && <Typography variant="body2">Day: {w.trigger.day_of_week}</Typography>}
            {w.trigger?.cron_expression && <Typography variant="body2">Cron: {w.trigger.cron_expression}</Typography>}
          </Paper>
        </Grid>

        {/* Steps */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Steps ({w.steps?.length || 0})</Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {(w.steps || []).map((step: any, idx: number) => (
                <Box key={step.id} sx={{ display: "flex", alignItems: "center", gap: 1, py: 1, borderBottom: "1px solid #eee" }}>
                  <Chip label={idx + 1} size="small" color="primary" />
                  <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }}>{step.name}</Typography>
                  <Chip label={step.action_type?.replace(/_/g, " ")} size="small" variant="outlined" />
                  {step.depends_on?.length > 0 && (
                    <Typography variant="caption" color="text.secondary">depends on: {step.depends_on.join(", ")}</Typography>
                  )}
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Conditions */}
        <Grid size={{ xs: 12 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Conditions</Typography>
            {(w.conditions || []).length === 0 ? (
              <Typography color="text.secondary">No conditions</Typography>
            ) : (
              (w.conditions || []).map((c: any, i: number) => (
                <Chip key={i} label={`${c.metric} ${c.operator} ${c.value}`} variant="outlined" sx={{ mr: 1, mb: 1 }} />
              ))
            )}
          </Paper>
        </Grid>

        {/* Metadata */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Metadata</Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
              <Typography variant="body2">Tags: {w.tags?.join(", ") || "None"}</Typography>
              <Typography variant="body2">Max Retries: {w.max_retries}</Typography>
              <Typography variant="body2">Timeout: {w.timeout_seconds}s</Typography>
              <Typography variant="body2">Last Run: {w.last_run_at || "Never"}</Typography>
              <Typography variant="body2">Next Run: {w.next_run_at || "Not scheduled"}</Typography>
              <Typography variant="body2">Created: {w.created_at}</Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
