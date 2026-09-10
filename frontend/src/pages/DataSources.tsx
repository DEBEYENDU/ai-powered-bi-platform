/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import RefreshIcon from "@mui/icons-material/Refresh";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import DownloadIcon from "@mui/icons-material/Download";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Dataset {
  dataset_id: string;
  name: string;
  row_count: number;
  column_count: number;
  file_size: number;
}

interface UploadResult {
  success: boolean;
  dataset_id: string;
  name: string;
  row_count: number;
  column_count: number;
  file_size: number;
  preview: Record<string, any>[];
  error: string | null;
}

interface ProfileResult {
  success: boolean;
  dataset_id: string;
  row_count: number;
  column_count: number;
  columns: {
    name: string;
    inferred_type: string;
    null_pct: number;
    unique_pct: number;
    duplicate_pct: number;
    mean_value: number | null;
    median_value: number | null;
    std_value: number | null;
    min_value: any;
    max_value: any;
  }[];
  quality_score: {
    overall: number;
    completeness: number;
    consistency: number;
    accuracy: number;
    uniqueness: number;
    validity: number;
  };
  ai_insights: string[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatBytes(bytes: number) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function ScoreBadge({ value }: { value: number }) {
  const color = value >= 80 ? "success" : value >= 60 ? "warning" : "error";
  return <Chip label={`${value}`} color={color} size="small" variant="outlined" />;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function DataSources() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [profileData, setProfileData] = useState<ProfileResult | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ datasets: Dataset[]; count: number }>("/ai/de/datasets");
      setDatasets(res.datasets || []);
    } catch (e: any) {
      setError(e.message || "Failed to load datasets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", file.name);
      formData.append("source_type", file.name.split(".").pop() || "csv");

      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch("/api/v1/ai/de/upload", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      const data: UploadResult = await res.json();
      if (!data.success) throw new Error(data.error || "Upload failed");
      await fetchDatasets();
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handlePreview = async (ds: Dataset) => {
    setSelectedDataset(ds);
    setPreviewOpen(true);
    setProfileLoading(true);
    setProfileData(null);
    try {
      const res = await rpost<ProfileResult>("/ai/de/profile", { dataset_id: ds.dataset_id });
      setProfileData(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setProfileLoading(false);
    }
  };

  const handleExport = async (ds: Dataset, format: string) => {
    try {
      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch("/api/v1/ai/de/export/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ dataset_id: ds.dataset_id, format }),
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${ds.name.replace(/\.[^.]+$/, "")}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Data Sources
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Upload, explore, and manage your datasets
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Upload Zone */}
      <Paper
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        sx={{
          p: 4,
          mb: 3,
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "grey.400",
          bgcolor: dragOver ? "action.hover" : "background.paper",
          cursor: "pointer",
          textAlign: "center",
          transition: "all 0.2s",
        }}
      >
        <input
          ref={fileRef}
          type="file"
          hidden
          accept=".csv,.xlsx,.xls,.json,.parquet"
          onChange={handleFileChange}
        />
        {uploading ? (
          <CircularProgress />
        ) : (
          <>
            <CloudUploadIcon sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
            <Typography variant="h6">Drop file here or click to upload</Typography>
            <Typography variant="body2" color="text.secondary">
              Supports CSV, Excel, JSON, Parquet
            </Typography>
          </>
        )}
      </Paper>

      {/* Dataset List */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">Datasets ({datasets.length})</Typography>
        <IconButton onClick={fetchDatasets} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : datasets.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No datasets uploaded yet</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell align="right">Rows</TableCell>
                <TableCell align="right">Columns</TableCell>
                <TableCell align="right">Size</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {datasets.map((ds) => (
                <TableRow key={ds.dataset_id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {ds.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {ds.dataset_id.slice(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell align="right">{ds.row_count.toLocaleString()}</TableCell>
                  <TableCell align="right">{ds.column_count}</TableCell>
                  <TableCell align="right">{formatBytes(ds.file_size)}</TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => handlePreview(ds)} title="Profile">
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleExport(ds, "csv")} title="Export CSV">
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleExport(ds, "excel")} title="Export Excel">
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Profile Preview Dialog */}
      <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Dataset Profile: {selectedDataset?.name}
          <IconButton
            onClick={() => setPreviewOpen(false)}
            sx={{ position: "absolute", right: 8, top: 8 }}
          >
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {profileLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
              <CircularProgress />
            </Box>
          ) : profileData ? (
            <Box>
              {/* Quality Scores */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                {[
                  ["Overall", profileData.quality_score.overall],
                  ["Completeness", profileData.quality_score.completeness],
                  ["Consistency", profileData.quality_score.consistency],
                  ["Accuracy", profileData.quality_score.accuracy],
                  ["Uniqueness", profileData.quality_score.uniqueness],
                  ["Validity", profileData.quality_score.validity],
                ].map(([label, score]) => (
                  <Grid key={label} size={{ xs: 6, md: 2 }}>
                    <Card>
                      <CardContent sx={{ textAlign: "center", p: 1.5, "&:last-child": { pb: 1.5 } }}>
                        <Typography variant="caption" color="text.secondary">
                          {label}
                        </Typography>
                        <ScoreBadge value={score as number} />
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>

              {/* Column Profiles */}
              <Typography variant="h6" sx={{ mb: 1 }}>
                Columns ({profileData.columns.length})
              </Typography>
              <TableContainer component={Paper} sx={{ mb: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Column</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell align="right">Null %</TableCell>
                      <TableCell align="right">Unique %</TableCell>
                      <TableCell align="right">Mean</TableCell>
                      <TableCell align="right">Min</TableCell>
                      <TableCell align="right">Max</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {profileData.columns.map((col) => (
                      <TableRow key={col.name} hover>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {col.name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={col.inferred_type} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell align="right">
                          {col.null_pct > 0 ? (
                            <Chip
                              label={`${col.null_pct}%`}
                              size="small"
                              color={col.null_pct > 10 ? "error" : col.null_pct > 5 ? "warning" : "default"}
                            />
                          ) : (
                            "0%"
                          )}
                        </TableCell>
                        <TableCell align="right">{col.unique_pct}%</TableCell>
                        <TableCell align="right">
                          {col.mean_value != null ? col.mean_value.toFixed(2) : "-"}
                        </TableCell>
                        <TableCell align="right">{col.min_value ?? "-"}</TableCell>
                        <TableCell align="right">{col.max_value ?? "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* AI Insights */}
              {profileData.ai_insights.length > 0 && (
                <>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    AI Insights
                  </Typography>
                  {profileData.ai_insights.map((insight, i) => (
                    <Alert key={i} severity="info" sx={{ mb: 1 }}>
                      {insight}
                    </Alert>
                  ))}
                </>
              )}
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
