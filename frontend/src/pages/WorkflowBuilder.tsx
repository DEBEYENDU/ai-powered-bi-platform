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
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import { rpost } from "../api";

interface Step {
  id: string; name: string; action_type: string; config: any; depends_on: string[];
}

const ACTION_TYPES = [
  "run_sql", "analyze_dataset", "generate_dashboard", "generate_report",
  "generate_forecast", "run_ai_agent", "send_email", "send_notification",
  "create_alert", "export_pdf", "export_excel", "export_powerpoint",
  "human_approval", "evaluate_condition",
];

const TRIGGER_TYPES = ["manual", "daily", "weekly", "monthly", "quarterly", "cron"];

export function WorkflowBuilder() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("manual");
  const [triggerTime, setTriggerTime] = useState("09:00");
  const [triggerDay, setTriggerDay] = useState("monday");
  const [triggerDayOfMonth, setTriggerDayOfMonth] = useState("1");
  const [cronExpression, setCronExpression] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [aiPrompt, setAiPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const addStep = () => {
    const id = `step_${steps.length + 1}`;
    setSteps([...steps, { id, name: `Step ${steps.length + 1}`, action_type: "run_sql", config: {}, depends_on: steps.length > 0 ? [steps[steps.length - 1].id] : [] }]);
  };

  const removeStep = (idx: number) => {
    const stepId = steps[idx].id;
    setSteps(steps.filter((_, i) => i !== idx).map(s => ({
      ...s, depends_on: s.depends_on.filter(d => d !== stepId),
    })));
  };

  const updateStep = (idx: number, field: string, value: any) => {
    const updated = [...steps];
    (updated[idx] as any)[field] = value;
    setSteps(updated);
  };

  const updateStepConfig = (idx: number, key: string, value: any) => {
    const updated = [...steps];
    updated[idx] = { ...updated[idx], config: { ...updated[idx].config, [key]: value } };
    setSteps(updated);
  };

  const handleSave = async () => {
    if (!name.trim()) { setError("Workflow name is required"); return; }
    setLoading(true);
    setError("");
    try {
      const trigger: any = { type: triggerType };
      if (triggerType === "cron") trigger.cron_expression = cronExpression;
      if (["daily", "scheduled"].includes(triggerType)) trigger.time = triggerTime;
      if (triggerType === "weekly") { trigger.day_of_week = triggerDay; trigger.time = triggerTime; }
      if (triggerType === "monthly") { trigger.day_of_month = parseInt(triggerDayOfMonth); trigger.time = triggerTime; }

      await rpost("/workflows", { name, description, trigger, steps, conditions: [], tags: [] });
      setSuccess("Workflow created successfully!");
      setTimeout(() => window.location.href = "/workflows", 1500);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleAIGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await rpost<any>("/workflows/ai/generate", { prompt: aiPrompt });
      if (res.success && res.workflow) {
        const wf = res.workflow;
        setName(wf.name || "AI-Generated Workflow");
        setDescription(wf.description || "");
        if (wf.trigger?.type) setTriggerType(wf.trigger.type);
        if (wf.steps) setSteps(wf.steps);
        if (res.validation_errors?.length) setError("Validation: " + res.validation_errors.join("; "));
        setSuccess("Workflow generated from AI. Review before saving.");
      } else {
        setError(res.error || "AI generation failed");
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Workflow Builder</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Create automated BI workflows visually or with AI assistance
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      {/* AI Builder */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: "primary.50", border: "1px solid", borderColor: "primary.200" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <SmartToyIcon color="primary" />
          <Typography variant="h6">AI Workflow Builder</Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Describe your workflow in natural language and let AI generate the structure
        </Typography>
        <Box sx={{ display: "flex", gap: 2, alignItems: "flex-end" }}>
          <TextField
            fullWidth multiline minRows={2} maxRows={4}
            label='e.g., "Every Monday at 9 AM, analyze sales and email the report to management"'
            value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)}
          />
          <Button variant="contained" onClick={handleAIGenerate} disabled={loading || !aiPrompt.trim()}
            startIcon={loading ? <CircularProgress size={18} /> : <SmartToyIcon />}
            sx={{ minWidth: 160, height: 56 }}>
            {loading ? "Generating..." : "Generate"}
          </Button>
        </Box>
      </Paper>

      {/* Basic Info */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Basic Information</Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField fullWidth label="Workflow Name" value={name} onChange={(e) => setName(e.target.value)} required />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField fullWidth label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          </Grid>
        </Grid>
      </Paper>

      {/* Trigger */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Trigger</Typography>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Select fullWidth value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
              {TRIGGER_TYPES.map((t) => <MenuItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</MenuItem>)}
            </Select>
          </Grid>
          {["daily", "weekly", "monthly"].includes(triggerType) && (
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField fullWidth label="Time" type="time" value={triggerTime}
                onChange={(e) => setTriggerTime(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
          )}
          {triggerType === "weekly" && (
            <Grid size={{ xs: 12, md: 3 }}>
              <Select fullWidth value={triggerDay} onChange={(e) => setTriggerDay(e.target.value)}>
                {["monday","tuesday","wednesday","thursday","friday","saturday","sunday"].map((d) => (
                  <MenuItem key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</MenuItem>
                ))}
              </Select>
            </Grid>
          )}
          {triggerType === "monthly" && (
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField fullWidth label="Day of Month" type="number" value={triggerDayOfMonth}
                onChange={(e) => setTriggerDayOfMonth(e.target.value)} />
            </Grid>
          )}
          {triggerType === "cron" && (
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="Cron Expression" value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)} placeholder="0 9 * * 1" />
            </Grid>
          )}
        </Grid>
      </Paper>

      {/* Steps */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">Steps ({steps.length})</Typography>
          <Button startIcon={<AddIcon />} onClick={addStep} variant="outlined" size="small">Add Step</Button>
        </Box>

        {steps.length === 0 ? (
          <Box sx={{ py: 3, textAlign: "center" }}>
            <Typography color="text.secondary">No steps added. Click "Add Step" or use the AI Builder.</Typography>
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {steps.map((step, idx) => (
              <Card key={step.id} sx={{ borderLeft: `4px solid ${idx === steps.length - 1 ? "#1976d2" : "#bdbdbd"}` }}>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                    <Chip label={step.id} size="small" color="primary" variant="outlined" />
                    <Button size="small" color="error" onClick={() => removeStep(idx)} startIcon={<DeleteIcon />}>Remove</Button>
                  </Box>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <TextField fullWidth label="Step Name" size="small" value={step.name}
                        onChange={(e) => updateStep(idx, "name", e.target.value)} />
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <Select fullWidth size="small" value={step.action_type}
                        onChange={(e) => updateStep(idx, "action_type", e.target.value)}>
                        {ACTION_TYPES.map((a) => <MenuItem key={a} value={a}>{a.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>)}
                      </Select>
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <TextField fullWidth label="Config (JSON)" size="small"
                        value={JSON.stringify(step.config)}
                        onChange={(e) => { try { updateStep(idx, "config", JSON.parse(e.target.value)); } catch {} }} />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Paper>

      {/* Save */}
      <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end" }}>
        <Button variant="outlined" onClick={() => window.location.href = "/workflows"}>Cancel</Button>
        <Button variant="contained" startIcon={loading ? <CircularProgress size={18} /> : <SaveIcon />}
          onClick={handleSave} disabled={loading || !name.trim()}>
          {loading ? "Saving..." : "Save Workflow"}
        </Button>
      </Box>
    </Box>
  );
}
