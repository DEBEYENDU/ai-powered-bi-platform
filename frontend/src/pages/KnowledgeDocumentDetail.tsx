/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
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
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ReplayIcon from "@mui/icons-material/Replay";
import DeleteIcon from "@mui/icons-material/Delete";
import DescriptionIcon from "@mui/icons-material/Description";
import { rget, rdel } from "../api";
import { useMutation } from "../components";
import { Loading, ErrorBanner, NoticeBanner, ConfirmDialog } from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DocumentDetail {
  document_id: string;
  filename: string;
  content_type: string;
  status: string;
  file_size: number;
  chunk_count: number;
  collection_id: string;
  collection_name: string;
  title: string;
  description: string;
  uploaded_by: string;
  created_at: string;
  indexed_at: string | null;
  updated_at: string;
  content_preview: string;
  metadata: Record<string, any>;
}

interface DocumentChunk {
  chunk_id: string;
  index: number;
  text: string;
  token_count: number;
  page_number: number | null;
  section: string | null;
  created_at: string;
}

interface StatusHistoryEntry {
  status: string;
  changed_at: string;
  message: string;
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

function StatusChip({ status }: { status: string }) {
  const color: Record<string, "success" | "warning" | "error" | "default" | "info"> = {
    indexed: "success",
    processing: "info",
    pending: "warning",
    failed: "error",
  };
  return <Chip label={status} color={color[status] || "default"} size="small" />;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function KnowledgeDocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [statusHistory, setStatusHistory] = useState<StatusHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const fetchDocument = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const res = await rget<DocumentDetail>(`/knowledge/documents/${id}`);
      setDocument(res);
    } catch (e: any) {
      setError(e.message || "Failed to load document");
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchChunks = useCallback(async () => {
    if (!id) return;
    try {
      const res = await rget<{ chunks: DocumentChunk[] }>(
        `/knowledge/documents/${id}/chunks`
      );
      setChunks(res.chunks || []);
    } catch {
      /* ignore */
    }
  }, [id]);

  const fetchStatusHistory = useCallback(async () => {
    if (!id) return;
    try {
      const res = await rget<{ history: StatusHistoryEntry[] }>(
        `/knowledge/documents/${id}/history`
      );
      setStatusHistory(res.history || []);
    } catch {
      /* ignore */
    }
  }, [id]);

  useEffect(() => {
    fetchDocument();
    fetchChunks();
    fetchStatusHistory();
  }, [fetchDocument, fetchChunks, fetchStatusHistory]);

  const { run: handleDelete, busy: deleteBusy } = useMutation(
    async () => {
      if (!id) return;
      await rdel(`/knowledge/documents/${id}`);
    },
    () => {
      setNotice("Document deleted successfully");
      setTimeout(() => {
        window.location.href = "/knowledge/documents";
      }, 1500);
    }
  );

  const handleReindex = async () => {
    if (!id) return;
    try {
      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch(`/api/v1/knowledge/documents/${id}/reindex`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) throw new Error("Reindex failed");
      setNotice("Document reindexing started");
      fetchDocument();
    } catch (e: any) {
      setError(e.message || "Reindex failed");
    }
  };

  if (loading) return <Loading />;

  return (
    <Box sx={{ p: 3 }}>
      <ErrorBanner error={error} />
      <NoticeBanner notice={notice} />

      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => {
            window.location.href = "/knowledge/documents";
          }}
        >
          Back
        </Button>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>
            {document?.filename || "Document"}
          </Typography>
          {document?.title && document.title !== document.filename && (
            <Typography variant="body2" color="text.secondary">
              {document.title}
            </Typography>
          )}
        </Box>
        <Button
          variant="outlined"
          startIcon={<ReplayIcon />}
          onClick={handleReindex}
        >
          Reindex
        </Button>
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={() => setDeleteConfirm(true)}
        >
          Delete
        </Button>
      </Box>

      {!document ? (
        <Typography color="text.secondary">Document not found</Typography>
      ) : (
        <Grid container spacing={3}>
          {/* Metadata */}
          <Grid size={{ xs: 12, md: 4 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Document Info
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Filename
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {document.filename}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Type
                </Typography>
                <Box>
                  <Chip label={document.content_type} size="small" variant="outlined" />
                </Box>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Status
                </Typography>
                <Box>
                  <StatusChip status={document.status} />
                </Box>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Size
                </Typography>
                <Typography variant="body2">{formatFileSize(document.file_size)}</Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Collection
                </Typography>
                <Typography variant="body2">{document.collection_name || "Default"}</Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Chunks
                </Typography>
                <Typography variant="body2">{document.chunk_count}</Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Uploaded By
                </Typography>
                <Typography variant="body2">{document.uploaded_by || "Unknown"}</Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Created
                </Typography>
                <Typography variant="body2">
                  {new Date(document.created_at).toLocaleString()}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Indexed
                </Typography>
                <Typography variant="body2">
                  {document.indexed_at
                    ? new Date(document.indexed_at).toLocaleString()
                    : "Not indexed"}
                </Typography>
              </Box>

              {document.description && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Description
                  </Typography>
                  <Typography variant="body2">{document.description}</Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Content Preview */}
          <Grid size={{ xs: 12, md: 8 }}>
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Content Preview
              </Typography>
              {document.content_preview ? (
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    maxHeight: 400,
                    overflow: "auto",
                    fontFamily: "monospace",
                    fontSize: "0.85rem",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.6,
                  }}
                >
                  {document.content_preview}
                </Paper>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No content preview available
                </Typography>
              )}
            </Paper>

            {/* Chunks */}
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Chunks ({chunks.length})
              </Typography>
              {chunks.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No chunks available
                </Typography>
              ) : (
                <Box>
                  {chunks.map((chunk) => (
                    <Paper
                      key={chunk.chunk_id}
                      variant="outlined"
                      sx={{ p: 2, mb: 1 }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          mb: 1,
                        }}
                      >
                        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                          <Chip
                            label={`Chunk ${chunk.index + 1}`}
                            size="small"
                            color="primary"
                          />
                          {chunk.page_number && (
                            <Chip
                              label={`Page ${chunk.page_number}`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                          {chunk.section && (
                            <Chip
                              label={chunk.section}
                              size="small"
                              variant="outlined"
                            />
                          )}
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {chunk.token_count} tokens
                        </Typography>
                      </Box>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                          fontFamily: "monospace",
                          fontSize: "0.85rem",
                          maxHeight: 120,
                          overflow: "auto",
                        }}
                      >
                        {chunk.text}
                      </Typography>
                    </Paper>
                  ))}
                </Box>
              )}
            </Paper>

            {/* Status History */}
            {statusHistory.length > 0 && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Status History
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Status</TableCell>
                        <TableCell>Changed At</TableCell>
                        <TableCell>Message</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {statusHistory.map((entry, idx) => (
                        <TableRow key={idx}>
                          <TableCell>
                            <StatusChip status={entry.status} />
                          </TableCell>
                          <TableCell>
                            {new Date(entry.changed_at).toLocaleString()}
                          </TableCell>
                          <TableCell>{entry.message || "-"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            )}
          </Grid>
        </Grid>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteConfirm}
        title="Delete Document"
        message={`Are you sure you want to delete "${document?.filename}"? This will also remove all associated chunks and cannot be undone.`}
        onCancel={() => setDeleteConfirm(false)}
        onConfirm={() => {
          setDeleteConfirm(false);
          handleDelete(undefined as any);
        }}
      />
    </Box>
  );
}
