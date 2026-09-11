/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box,
  Chip,
  CircularProgress,
  Paper,
  Typography,
} from "@mui/material";
import { rget } from "../api";

export function WorkflowExecutionDetails() {
  const { executionId } = useParams<{ executionId: string }>();
  const [execution, setExecution] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!executionId) return;
    rget<any>(`/workflows/executions/${executionId}`)
      .then((res) => setExecution(res))
      .finally(() => setLoading(false));
  }, [executionId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}><CircularProgress /></Box>;
  if (!execution?.success) return <Typography color="error">Execution not found</Typography>;

  const e = execution;
  const statusColor: Record<string, "success" | "error" | "info" | "default"> = {
    completed: "success", failed: "error", running: "info",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Execution Details</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Detailed view of workflow execution {e.id}
      </Typography>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 2 }}>
          <Chip label={e.status} color={statusColor[e.status] || "default"} />
          <Chip label={`Trigger: ${e.trigger_type}`} variant="outlined" />
          {e.is_test && <Chip label="TEST" color="warning" />}
          <Chip label={`Duration: ${(e.duration_ms / 1000).toFixed(1)}s`} />
        </Box>
        <Typography variant="body2">Started: {e.started_at}</Typography>
        <Typography variant="body2">Completed: {e.completed_at || "In progress"}</Typography>
        {e.errors?.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" color="error.main" sx={{ fontWeight: 600 }}>Errors:</Typography>
            {e.errors.map((err: string, i: number) => (
              <Typography key={i} variant="body2" color="error.main">- {err}</Typography>
            ))}
          </Box>
        )}
      </Paper>

      <Typography variant="h6" sx={{ mb: 2 }}>Step Executions</Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {(e.steps || []).map((step: any, idx: number) => (
          <Paper key={step.id} sx={{ p: 2, borderLeft: `4px solid ${step.status === "completed" ? "#4caf50" : step.status === "failed" ? "#f44336" : "#bdbdbd"}` }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
              <Chip label={idx + 1} size="small" color="primary" />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>{step.step_name}</Typography>
              <Chip label={step.status} color={statusColor[step.status] || "default"} size="small" />
              <Chip label={step.action_type?.replace(/_/g, " ")} size="small" variant="outlined" />
              {step.retry_count > 0 && <Chip label={`Retries: ${step.retry_count}`} size="small" color="warning" variant="outlined" />}
            </Box>
            <Typography variant="body2" color="text.secondary">Duration: {step.duration_ms?.toFixed(0) || 0}ms</Typography>
            {step.error && <Typography variant="body2" color="error.main" sx={{ mt: 1 }}>{step.error}</Typography>}
            {step.output_data && Object.keys(step.output_data).length > 0 && (
              <Box sx={{ mt: 1, p: 1, bgcolor: "grey.50", borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary">Output: {JSON.stringify(step.output_data).slice(0, 200)}</Typography>
              </Box>
            )}
          </Paper>
        ))}
      </Box>
    </Box>
  );
}
