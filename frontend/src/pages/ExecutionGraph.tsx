/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Paper,
  Typography,
} from "@mui/material";
import { rget } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TaskStep {
  step_id: string;
  agent_type: string;
  description: string;
  input_data: any;
  output_data: any;
  status: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  error: string | null;
  retries: number;
}

interface TaskRecord {
  task_id: string;
  task: string;
  agent_sequence: string[];
  duration_ms: number;
  failures: number;
  completed_at: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function StepNode({ step, isLast }: { step: TaskStep; isLast: boolean }) {
  const statusColor: Record<string, "success" | "error" | "warning" | "default" | "info"> = {
    completed: "success",
    failed: "error",
    running: "info",
    pending: "default",
  };

  return (
    <Box sx={{ display: "flex", gap: 2 }}>
      {/* Timeline dot + line */}
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 24 }}>
        <Box
          sx={{
            width: 16,
            height: 16,
            borderRadius: "50%",
            bgcolor: step.status === "completed" ? "success.main" : step.status === "failed" ? "error.main" : "grey.400",
            border: 2,
            borderColor: "white",
            boxShadow: 1,
          }}
        />
        {!isLast && (
          <Box sx={{ width: 2, flex: 1, bgcolor: "grey.300", my: 0.5 }} />
        )}
      </Box>

      {/* Step content */}
      <Paper sx={{ p: 2, mb: 2, flex: 1, borderLeft: `4px solid ${step.status === "completed" ? "#4caf50" : step.status === "failed" ? "#f44336" : "#bdbdbd"}` }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <Chip label={step.agent_type} color={statusColor[step.status] || "default"} size="small" />
          <Typography variant="caption" color="text.secondary">
            {step.duration_ms > 0 ? `${step.duration_ms.toFixed(0)}ms` : "pending"}
          </Typography>
          {step.retries > 0 && (
            <Chip label={`retry ×${step.retries}`} size="small" color="warning" variant="outlined" />
          )}
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{step.description}</Typography>
        {step.error && (
          <Alert severity="error" sx={{ mt: 1 }}>
            <Typography variant="caption">{step.error}</Typography>
          </Alert>
        )}
        {step.output_data && step.status === "completed" && (
          <Box sx={{ mt: 1, p: 1, bgcolor: "grey.50", borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Output keys: {Object.keys(step.output_data).join(", ")}
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function ExecutionGraph() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [error, setError] = useState("");

  const loadTasks = useCallback(() => {
    rget<{ tasks: TaskRecord[] }>("/ai/agents/tasks?limit=20")
      .then((res) => {
        const list = res.tasks || [];
        setTasks(list);
        if (list.length > 0 && !selectedTask) {
          setSelectedTask(list[0].task_id);
        }
      })
      .catch((e) => setError(e.message));
  }, [selectedTask]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  useEffect(() => {
    if (!selectedTask) return;
    rget<{ tasks: any[] }>("/ai/agents/tasks?limit=100")
      .then((res) => {
        const task = (res.tasks || []).find((t: any) => t.task_id === selectedTask);
        if (task) {
          // The steps are embedded in the task history - we use agent_sequence as fallback
          setTaskSteps([]);
        }
      })
      .catch(() => {});
  }, [selectedTask]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Execution Graph</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Visualize the multi-agent task execution pipeline and step-by-step flow
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      {/* Task selector */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Select Task</Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {tasks.map((t) => (
            <Chip
              key={t.task_id}
              label={`${t.task.slice(0, 40)}... (${t.task_id})`}
              onClick={() => setSelectedTask(t.task_id)}
              color={selectedTask === t.task_id ? "primary" : "default"}
              variant={selectedTask === t.task_id ? "filled" : "outlined"}
            />
          ))}
          {tasks.length === 0 && (
            <Typography variant="body2" color="text.secondary">No tasks available</Typography>
          )}
        </Box>
      </Paper>

      {/* Execution timeline */}
      {selectedTask && (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">Execution Timeline</Typography>
            {tasks.find((t) => t.task_id === selectedTask) && (
              <Box sx={{ display: "flex", gap: 1 }}>
                <Chip label={`${tasks.find((t) => t.task_id === selectedTask)?.agent_sequence.length || 0} agents`} size="small" />
                <Chip
                  label={`${((tasks.find((t) => t.task_id === selectedTask)?.duration_ms || 0) / 1000).toFixed(1)}s`}
                  size="small"
                  color="info"
                />
              </Box>
            )}
          </Box>

          {taskSteps.length > 0 ? (
            <Box>
              {taskSteps.map((step, i) => (
                <StepNode key={step.step_id} step={step} isLast={i === taskSteps.length - 1} />
              ))}
            </Box>
          ) : (
            <Box sx={{ py: 4, textAlign: "center" }}>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
                Agent Sequence: {tasks.find((t) => t.task_id === selectedTask)?.agent_sequence.join(" → ") || "N/A"}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Step-level execution details are logged in real-time.
                {tasks.find((t) => t.task_id === selectedTask)?.failures === 0
                  ? " All steps completed successfully."
                  : ` ${tasks.find((t) => t.task_id === selectedTask)?.failures} step(s) failed.`}
              </Typography>
            </Box>
          )}
        </Paper>
      )}
    </Box>
  );
}
