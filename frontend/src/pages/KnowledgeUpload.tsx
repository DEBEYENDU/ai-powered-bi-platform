/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import { rget } from "../api";
import { Loading, ErrorBanner, NoticeBanner } from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Collection {
  collection_id: string;
  name: string;
}

interface UploadJob {
  job_id: string;
  filename: string;
  status: string;
  document_id: string | null;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function KnowledgeUpload() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploadJobs, setUploadJobs] = useState<UploadJob[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchCollections = useCallback(async () => {
    try {
      const res = await rget<{ collections: Collection[] }>("/knowledge/collections");
      setCollections(res.collections || []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError("");
    setNotice("");
    setUploadProgress(0);

    const jobId = `upload-${Date.now()}`;
    const newJob: UploadJob = {
      job_id: jobId,
      filename: file.name,
      status: "uploading",
      document_id: null,
      error: null,
    };
    setUploadJobs((prev) => [newJob, ...prev]);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (selectedCollection) formData.append("collection_id", selectedCollection);
      if (title) formData.append("title", title);
      if (description) formData.append("description", description);

      const token = localStorage.getItem("bi_token") || "";

      const xhr = new XMLHttpRequest();
      const uploadPromise = new Promise<UploadJob>((resolve, reject) => {
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            setUploadProgress(Math.round((e.loaded / e.total) * 100));
          }
        });

        xhr.addEventListener("load", () => {
          try {
            const data = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve({
                job_id: data.job_id || jobId,
                filename: file.name,
                status: data.status || "processing",
                document_id: data.document_id || null,
                error: null,
              });
            } else {
              reject(new Error(data.detail || data.error || "Upload failed"));
            }
          } catch {
            reject(new Error("Invalid response from server"));
          }
        });

        xhr.addEventListener("error", () => reject(new Error("Network error during upload")));

        xhr.open("POST", "/api/v1/knowledge/documents/upload");
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.send(formData);
      });

      const result = await uploadPromise;

      setUploadJobs((prev) =>
        prev.map((j) => (j.job_id === jobId ? { ...j, ...result } : j))
      );

      setNotice(`"${file.name}" uploaded successfully. Processing has started.`);
      setTitle("");
      setDescription("");
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setUploadJobs((prev) =>
        prev.map((j) =>
          j.job_id === jobId ? { ...j, status: "failed", error: e.message } : j
        )
      );
    } finally {
      setUploading(false);
      setUploadProgress(0);
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
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleBulkUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => handleUpload(file));
    if (inputRef.current) inputRef.current.value = "";
  };

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case "indexed":
      case "completed":
        return <CheckCircleIcon sx={{ fontSize: 20, color: "success.main" }} />;
      case "failed":
      case "error":
        return <ErrorIcon sx={{ fontSize: 20, color: "error.main" }} />;
      case "processing":
      case "uploading":
      case "pending":
        return <HourglassEmptyIcon sx={{ fontSize: 20, color: "info.main" }} />;
      default:
        return null;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Upload Documents
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Add documents to your knowledge base for indexing and retrieval
      </Typography>

      <ErrorBanner error={error} />
      <NoticeBanner notice={notice} />

      <Grid container spacing={3}>
        {/* Upload Zone */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper
            sx={{
              p: 4,
              textAlign: "center",
              border: "2px dashed",
              borderColor: dragOver ? "primary.main" : "grey.400",
              bgcolor: dragOver ? "action.hover" : "background.paper",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              hidden
              accept=".txt,.md,.pdf,.docx,.csv"
              onChange={handleFileChange}
              multiple
            />
            {uploading ? (
              <Box>
                <CircularProgress />
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Uploading... {uploadProgress}%
                </Typography>
                <Box
                  sx={{
                    mt: 1,
                    height: 4,
                    bgcolor: "grey.800",
                    borderRadius: 2,
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      height: "100%",
                      width: `${uploadProgress}%`,
                      bgcolor: "primary.main",
                      transition: "width 0.3s",
                    }}
                  />
                </Box>
              </Box>
            ) : (
              <>
                <CloudUploadIcon sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
                <Typography variant="h6">Drag & drop files here or click to browse</Typography>
                <Typography variant="body2" color="text.secondary">
                  Supported: TXT, Markdown, PDF, DOCX, CSV (max 50MB)
                </Typography>
              </>
            )}
          </Paper>
        </Grid>

        {/* Options */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
              Upload Options
            </Typography>

            <TextField
              select
              fullWidth
              size="small"
              label="Collection"
              value={selectedCollection}
              onChange={(e) => setSelectedCollection(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ mb: 2 }}
            >
              <MenuItem value="">
                <em>Default Collection</em>
              </MenuItem>
              {collections.map((c) => (
                <MenuItem key={c.collection_id} value={c.collection_id}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              fullWidth
              size="small"
              label="Title (optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              size="small"
              label="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              multiline
              rows={3}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ mb: 2 }}
            />

            <Button
              variant="outlined"
              fullWidth
              component="label"
              disabled={uploading}
            >
              Choose Files
              <input
                type="file"
                hidden
                accept=".txt,.md,.pdf,.docx,.csv"
                multiple
                onChange={handleBulkUpload}
              />
            </Button>
          </Paper>
        </Grid>
      </Grid>

      {/* Upload Jobs */}
      {uploadJobs.length > 0 && (
        <Paper sx={{ p: 2, mt: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Upload History
          </Typography>
          {uploadJobs.map((job) => (
            <Box
              key={job.job_id}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                py: 1,
                borderBottom: "1px solid",
                borderColor: "divider",
                "&:last-child": { borderBottom: 0 },
              }}
            >
              <StatusIcon status={job.status} />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {job.filename}
                </Typography>
                {job.error && (
                  <Typography variant="caption" color="error.main">
                    {job.error}
                  </Typography>
                )}
              </Box>
              <Chip
                label={job.status}
                size="small"
                color={
                  job.status === "indexed" || job.status === "completed"
                    ? "success"
                    : job.status === "failed"
                    ? "error"
                    : "default"
                }
              />
            </Box>
          ))}
        </Paper>
      )}
    </Box>
  );
}
