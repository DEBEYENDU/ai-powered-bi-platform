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
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import InfoIcon from "@mui/icons-material/Info";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Dataset {
  dataset_id: string;
  name: string;
  row_count: number;
}

interface QualityIssue {
  id: string;
  dimension: string;
  severity: string;
  column: string;
  issue_type: string;
  description: string;
  affected_rows: number;
  affected_pct: number;
  suggestion: string;
}

interface QualityScore {
  overall: number;
  completeness: number;
  consistency: number;
  accuracy: number;
  uniqueness: number;
  validity: number;
  timeliness: number;
}

interface ValidationResult {
  success: boolean;
  dataset_id: string;
  issues: QualityIssue[];
  quality_score: QualityScore;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  validation_time_ms: number;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function ScoreCard({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? "#4caf50" : value >= 60 ? "#ff9800" : "#f44336";
  return (
    <Card>
      <CardContent sx={{ textAlign: "center" }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ color, fontWeight: 700 }}>
          {value}
        </Typography>
        <LinearProgress
          variant="determinate"
          value={value}
          sx={{
            mt: 1,
            height: 6,
            borderRadius: 3,
            bgcolor: "grey.200",
            "& .MuiLinearProgress-bar": { bgcolor: color, borderRadius: 3 },
          }}
        />
      </CardContent>
    </Card>
  );
}

function SeverityIcon({ severity }: { severity: string }) {
  switch (severity) {
    case "critical":
      return <ErrorIcon sx={{ color: "error.main", fontSize: 18 }} />;
    case "high":
      return <WarningAmberIcon sx={{ color: "warning.main", fontSize: 18 }} />;
    case "medium":
      return <InfoIcon sx={{ color: "info.main", fontSize: 18 }} />;
    default:
      return <CheckCircleIcon sx={{ color: "success.main", fontSize: 18 }} />;
  }
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function DataQuality() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    rget<{ datasets: Dataset[] }>("/ai/de/datasets")
      .then((res) => setDatasets(res.datasets || []))
      .catch((e) => setError(e.message));
  }, []);

  const handleValidate = async () => {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await rpost<ValidationResult>("/ai/de/validate", {
        dataset_id: selectedId,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Validation failed");
    } finally {
      setLoading(false);
    }
  };

  const dimensionLabels: Record<string, string> = {
    completeness: "Completeness",
    consistency: "Consistency",
    accuracy: "Accuracy",
    uniqueness: "Uniqueness",
    validity: "Validity",
    timeliness: "Timeliness",
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Data Quality
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Validate datasets and monitor quality scores
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
              onClick={handleValidate}
              disabled={!selectedId || loading}
              fullWidth
            >
              {loading ? <CircularProgress size={20} /> : "Run Validation"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Results */}
      {result && (
        <>
          {/* Quality Score Cards */}
          <Typography variant="h6" sx={{ mb: 2 }}>
            Quality Scores
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Overall" value={result.quality_score.overall} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Completeness" value={result.quality_score.completeness} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Consistency" value={result.quality_score.consistency} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Accuracy" value={result.quality_score.accuracy} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Uniqueness" value={result.quality_score.uniqueness} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Validity" value={result.quality_score.validity} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <ScoreCard label="Timeliness" value={result.quality_score.timeliness} />
            </Grid>
          </Grid>

          {/* Summary */}
          <Alert severity={result.issues.length === 0 ? "success" : "warning"} sx={{ mb: 2 }}>
            {result.failed_checks} issues found across {result.total_checks} checks
            ({result.validation_time_ms}ms)
          </Alert>

          {/* Issues Table */}
          {result.issues.length > 0 && (
            <>
              <Typography variant="h6" sx={{ mb: 1 }}>
                Issues ({result.issues.length})
              </Typography>
              <TableContainer component={Paper}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={40}></TableCell>
                      <TableCell>Column</TableCell>
                      <TableCell>Issue</TableCell>
                      <TableCell>Dimension</TableCell>
                      <TableCell align="right">Affected</TableCell>
                      <TableCell>Suggestion</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.issues.map((issue) => (
                      <TableRow key={issue.id} hover>
                        <TableCell>
                          <SeverityIcon severity={issue.severity} />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {issue.column || "-"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{issue.description}</Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={dimensionLabels[issue.dimension] || issue.dimension}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {issue.affected_rows.toLocaleString()}
                          {issue.affected_pct > 0 && (
                            <Typography variant="caption" sx={{ display: "block" }} color="text.secondary">
                              {issue.affected_pct}%
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {issue.suggestion}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </>
      )}
    </Box>
  );
}
