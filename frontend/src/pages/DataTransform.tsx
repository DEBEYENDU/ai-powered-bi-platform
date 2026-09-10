/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Dataset {
  dataset_id: string;
  name: string;
  row_count: number;
}

interface TransformType {
  type: string;
  name: string;
  description: string;
  parameters: Record<string, string>;
}

interface TransformStep {
  id: string;
  transform_type: string;
  column: string;
  parameters: Record<string, any>;
}

interface TransformResult {
  success: boolean;
  dataset_id: string;
  new_dataset_id: string;
  transforms_applied: number;
  rows_before: number;
  rows_after: number;
  columns_added: string[];
  columns_removed: string[];
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function DataTransform() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [transformTypes, setTransformTypes] = useState<TransformType[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [steps, setSteps] = useState<TransformStep[]>([]);
  const [result, setResult] = useState<TransformResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    rget<{ datasets: Dataset[] }>("/ai/de/datasets")
      .then((res) => setDatasets(res.datasets || []))
      .catch((e) => setError(e.message));
    rget<TransformType[]>("/ai/de/transforms")
      .then((res) => setTransformTypes(res || []))
      .catch(() => {});
  }, []);

  const addStep = () => {
    setSteps((prev) => [
      ...prev,
      {
        id: crypto.randomUUID().slice(0, 8),
        transform_type: "",
        column: "",
        parameters: {},
      },
    ]);
  };

  const removeStep = (id: string) => {
    setSteps((prev) => prev.filter((s) => s.id !== id));
  };

  const updateStep = (id: string, field: string, value: any) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
  };

  const handleRun = async () => {
    if (!selectedId || steps.length === 0) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const transforms = steps
        .filter((s) => s.transform_type)
        .map((s) => ({
          transform_type: s.transform_type,
          column: s.column,
          parameters: s.parameters,
        }));
      const res = await rpost<TransformResult>("/ai/de/transform", {
        dataset_id: selectedId,
        transforms,
        create_version: true,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Transform failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSavePipeline = async () => {
    if (!selectedId || steps.length === 0) return;
    const name = prompt("Pipeline name:");
    if (!name) return;
    try {
      await rpost("/ai/de/pipelines", {
        name,
        dataset_id: selectedId,
        steps: steps
          .filter((s) => s.transform_type)
          .map((s, i) => ({ ...s, order: i + 1 })),
      });
      alert("Pipeline saved!");
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Transformation Builder
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Build and execute data transformations step by step
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Dataset Selection */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Select
              fullWidth
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              displayEmpty
            >
              <MenuItem value="">
                <em>Select a dataset</em>
              </MenuItem>
              {datasets.map((ds) => (
                <MenuItem key={ds.dataset_id} value={ds.dataset_id}>
                  {ds.name} ({ds.row_count.toLocaleString()} rows)
                </MenuItem>
              ))}
            </Select>
          </Grid>
          <Grid size={{ xs: 6, md: 2 }}>
            <Button
              variant="outlined"
              onClick={addStep}
              startIcon={<AddIcon />}
              fullWidth
              disabled={!selectedId}
            >
              Add Step
            </Button>
          </Grid>
          <Grid size={{ xs: 6, md: 2 }}>
            <Button
              variant="contained"
              onClick={handleRun}
              disabled={!selectedId || steps.length === 0 || loading}
              startIcon={loading ? <CircularProgress size={18} /> : <PlayArrowIcon />}
              fullWidth
            >
              {loading ? "Running..." : "Run"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Transform Steps */}
      {steps.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
            <Typography variant="h6">Steps ({steps.length})</Typography>
            <Button
              size="small"
              onClick={handleSavePipeline}
              startIcon={<SaveIcon />}
              disabled={!selectedId}
            >
              Save as Pipeline
            </Button>
          </Box>
          {steps.map((step, idx) => (
            <Card key={step.id} sx={{ mb: 1 }}>
              <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Chip label={idx + 1} size="small" color="primary" />
                  <FormControl size="small" sx={{ minWidth: 160 }}>
                    <InputLabel>Operation</InputLabel>
                    <Select
                      value={step.transform_type}
                      label="Operation"
                      onChange={(e) => updateStep(step.id, "transform_type", e.target.value)}
                    >
                      {transformTypes.map((t) => (
                        <MenuItem key={t.type} value={t.type}>
                          {t.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    size="small"
                    label="Column"
                    value={step.column}
                    onChange={(e) => updateStep(step.id, "column", e.target.value)}
                    sx={{ minWidth: 140 }}
                  />
                  <TextField
                    size="small"
                    label="Parameters (JSON)"
                    value={JSON.stringify(step.parameters)}
                    onChange={(e) => {
                      try {
                        updateStep(step.id, "parameters", JSON.parse(e.target.value));
                      } catch {
                        // ignore
                      }
                    }}
                    sx={{ flex: 1 }}
                  />
                  <IconButton size="small" onClick={() => removeStep(step.id)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Result */}
      {result && (
        <Alert severity={result.success ? "success" : "error"} sx={{ mb: 2 }}>
          {result.success ? (
            <>
              Applied {result.transforms_applied} transforms |
              Rows: {result.rows_before} → {result.rows_after}
              {result.columns_added.length > 0 && (
                <> | Added: {result.columns_added.join(", ")}</>
              )}
              {result.columns_removed.length > 0 && (
                <> | Removed: {result.columns_removed.join(", ")}</>
              )}
            </>
          ) : (
            result.error
          )}
        </Alert>
      )}

      {steps.length === 0 && !loading && (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">
            Select a dataset and click "Add Step" to start building transformations
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
