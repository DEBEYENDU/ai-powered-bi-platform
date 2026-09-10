/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import BuildIcon from "@mui/icons-material/Build";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Dataset {
  dataset_id: string;
  name: string;
  row_count: number;
}

interface CleaningSuggestion {
  id: string;
  column: string;
  transform_type: string;
  description: string;
  current_state: string;
  proposed_state: string;
  affected_rows: number;
  confidence: number;
  auto_applicable: boolean;
  parameters: Record<string, any>;
}

interface CleanResult {
  success: boolean;
  dataset_id: string;
  new_dataset_id: string;
  suggestions: CleaningSuggestion[];
  applied: string[];
  rows_before: number;
  rows_after: number;
  cells_modified: number;
  quality_before: { overall: number };
  quality_after: { overall: number };
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function DataCleaning() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [suggestions, setSuggestions] = useState<CleaningSuggestion[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<CleanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    rget<{ datasets: Dataset[] }>("/ai/de/datasets")
      .then((res) => setDatasets(res.datasets || []))
      .catch((e) => setError(e.message));
  }, []);

  const handleAnalyze = async () => {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    setSuggestions([]);
    setResult(null);
    setSelected(new Set());
    try {
      const res = await rpost<CleanResult>("/ai/de/clean", {
        dataset_id: selectedId,
        auto_clean: false,
      });
      setSuggestions(res.suggestions || []);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!selectedId || selected.size === 0) return;
    setApplying(true);
    setError("");
    try {
      const res = await rpost<CleanResult>("/ai/de/clean", {
        dataset_id: selectedId,
        auto_clean: false,
        rules: suggestions
          .filter((s) => selected.has(s.id))
          .map((s) => ({ type: s.transform_type, column: s.column })),
      });
      setResult(res);
      setSelected(new Set());
      if (res.applied.length > 0) {
        setSuggestions((prev) => prev.filter((s) => !selected.has(s.id)));
      }
    } catch (e: any) {
      setError(e.message || "Apply failed");
    } finally {
      setApplying(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === suggestions.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(suggestions.map((s) => s.id)));
    }
  };

  const typeLabel: Record<string, string> = {
    fill_missing: "Fill Missing",
    remove_duplicates: "Remove Duplicates",
    trim_spaces: "Trim Spaces",
    standardize: "Standardize",
    normalize_text: "Normalize Text",
    convert_type: "Convert Type",
    rename: "Rename",
    drop: "Drop Column",
    filter: "Filter Rows",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Cleaning Suggestions
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        AI-powered cleaning recommendations for your datasets
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: "center" }}>
          <Grid size={{ xs: 12, md: 6 }}>
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
          <Grid size={{ xs: 12, md: 6 }}>
            <Button
              variant="contained"
              onClick={handleAnalyze}
              disabled={!selectedId || loading}
              startIcon={loading ? <CircularProgress size={18} /> : <AutoFixHighIcon />}
              fullWidth
            >
              {loading ? "Analyzing..." : "Analyze & Suggest"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Results */}
      {result && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Quality score: {result.quality_before.overall} → {result.quality_after.overall} |
          {result.suggestions.length} suggestions found
        </Alert>
      )}

      {suggestions.length > 0 && (
        <>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
            <Typography variant="h6">
              Suggestions ({suggestions.length})
              {selected.size > 0 && (
                <Chip label={`${selected.size} selected`} size="small" sx={{ ml: 1 }} />
              )}
            </Typography>
            <Box>
              <Button size="small" onClick={toggleAll} sx={{ mr: 1 }}>
                {selected.size === suggestions.length ? "Deselect All" : "Select All"}
              </Button>
              <Button
                variant="contained"
                size="small"
                onClick={handleApply}
                disabled={selected.size === 0 || applying}
                startIcon={applying ? <CircularProgress size={16} /> : <BuildIcon />}
              >
                {applying ? "Applying..." : `Apply (${selected.size})`}
              </Button>
            </Box>
          </Box>

          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selected.size === suggestions.length && suggestions.length > 0}
                      indeterminate={selected.size > 0 && selected.size < suggestions.length}
                      onChange={toggleAll}
                    />
                  </TableCell>
                  <TableCell>Column</TableCell>
                  <TableCell>Operation</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell align="right">Affected Rows</TableCell>
                  <TableCell align="right">Confidence</TableCell>
                  <TableCell>Auto</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {suggestions.map((sug) => (
                  <TableRow key={sug.id} hover selected={selected.has(sug.id)}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selected.has(sug.id)}
                        onChange={() => toggleSelect(sug.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {sug.column}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={typeLabel[sug.transform_type] || sug.transform_type}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{sug.description}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      {sug.affected_rows.toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      <Chip
                        label={`${(sug.confidence * 100).toFixed(0)}%`}
                        size="small"
                        color={sug.confidence > 0.8 ? "success" : sug.confidence > 0.5 ? "warning" : "default"}
                      />
                    </TableCell>
                    <TableCell>
                      {sug.auto_applicable && (
                        <Chip label="Auto" size="small" color="success" variant="outlined" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {!loading && suggestions.length === 0 && result && (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No cleaning suggestions — dataset looks good!</Typography>
        </Paper>
      )}
    </Box>
  );
}
