/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
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
import DescriptionIcon from "@mui/icons-material/Description";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import ErrorIcon from "@mui/icons-material/Error";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import SearchIcon from "@mui/icons-material/Search";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { rget } from "../api";
import { Loading, ErrorBanner, EmptyState } from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DocumentSummary {
  total_documents: number;
  indexed: number;
  processing: number;
  failed: number;
  total_collections: number;
  total_chunks: number;
}

interface RecentDocument {
  document_id: string;
  filename: string;
  content_type: string;
  status: string;
  file_size: number;
  chunk_count: number;
  collection_name: string;
  created_at: string;
  indexed_at: string | null;
}

interface CollectionSummary {
  collection_id: string;
  name: string;
  document_count: number;
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

export function KnowledgeBase() {
  const [summary, setSummary] = useState<DocumentSummary | null>(null);
  const [documents, setDocuments] = useState<RecentDocument[]>([]);
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [docsRes, collsRes] = await Promise.all([
        rget<{ documents: RecentDocument[]; total: number }>("/knowledge/documents?pageSize=10"),
        rget<{ collections: CollectionSummary[] }>("/knowledge/collections"),
      ]);

      const docs = docsRes.documents || [];
      const colls = collsRes.collections || [];

      const indexed = docs.filter((d) => d.status === "indexed").length;
      const processing = docs.filter((d) => d.status === "processing").length;
      const failed = docs.filter((d) => d.status === "failed").length;
      const totalChunks = docs.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

      setSummary({
        total_documents: docsRes.total || docs.length,
        indexed,
        processing,
        failed,
        total_collections: colls.length,
        total_chunks: totalChunks,
      });

      setDocuments(docs);
      setCollections(colls);
    } catch (e: any) {
      setError(e.message || "Failed to load knowledge base data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) return <Loading />;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Knowledge Base
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage documents, collections, and retrieval-augmented generation
      </Typography>

      <ErrorBanner error={error} />

      {/* Summary Stat Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <DescriptionIcon sx={{ fontSize: 32, color: "primary.main", mb: 0.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {summary?.total_documents ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total Documents
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <CheckCircleIcon sx={{ fontSize: 32, color: "success.main", mb: 0.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 700, color: "success.main" }}>
                {summary?.indexed ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Indexed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <HourglassEmptyIcon sx={{ fontSize: 32, color: "info.main", mb: 0.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 700, color: "info.main" }}>
                {summary?.processing ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Processing
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <ErrorIcon sx={{ fontSize: 32, color: "error.main", mb: 0.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 700, color: "error.main" }}>
                {summary?.failed ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Failed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <LibraryBooksIcon sx={{ fontSize: 32, color: "warning.main", mb: 0.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {summary?.total_collections ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Collections
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <DescriptionIcon sx={{ fontSize: 32, color: "text.secondary", mb: 0.5 }} />
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {summary?.total_chunks ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total Chunks
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Quick Actions
        </Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Button
            variant="contained"
            startIcon={<CloudUploadIcon />}
            onClick={() => {
              window.location.href = "/knowledge/upload";
            }}
          >
            Upload Document
          </Button>
          <Button
            variant="outlined"
            startIcon={<SearchIcon />}
            onClick={() => {
              window.location.href = "/knowledge/search";
            }}
          >
            Search Knowledge
          </Button>
          <Button
            variant="outlined"
            startIcon={<LibraryBooksIcon />}
            onClick={() => {
              window.location.href = "/knowledge/collections";
            }}
          >
            Manage Collections
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              window.location.href = "/knowledge/chat";
            }}
          >
            RAG Chat
          </Button>
        </Box>
      </Paper>

      {/* Recent Documents */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">Recent Documents</Typography>
          <Button
            variant="text"
            size="small"
            onClick={() => {
              window.location.href = "/knowledge/documents";
            }}
          >
            View All
          </Button>
        </Box>

        {documents.length === 0 ? (
          <EmptyState message="No documents uploaded yet" />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Filename</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Collection</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Size</TableCell>
                  <TableCell align="right">Chunks</TableCell>
                  <TableCell>Uploaded</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow
                    key={doc.document_id}
                    hover
                    sx={{ cursor: "pointer" }}
                    onClick={() => {
                      window.location.href = `/knowledge/documents/${doc.document_id}`;
                    }}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {doc.filename}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={doc.content_type} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{doc.collection_name || "-"}</TableCell>
                    <TableCell>
                      <StatusChip status={doc.status} />
                    </TableCell>
                    <TableCell align="right">{formatFileSize(doc.file_size)}</TableCell>
                    <TableCell align="right">{doc.chunk_count}</TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Collections Overview */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">Collections</Typography>
          <Button
            variant="text"
            size="small"
            onClick={() => {
              window.location.href = "/knowledge/collections";
            }}
          >
            Manage
          </Button>
        </Box>

        {collections.length === 0 ? (
          <EmptyState message="No collections created yet" />
        ) : (
          <Grid container spacing={2}>
            {collections.map((coll) => (
              <Grid key={coll.collection_id} size={{ xs: 12, sm: 6, md: 4 }}>
                <Card
                  sx={{ cursor: "pointer" }}
                  onClick={() => {
                    window.location.href = `/knowledge/collections/${coll.collection_id}`;
                  }}
                >
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {coll.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {coll.document_count} document{coll.document_count !== 1 ? "s" : ""}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Paper>
    </Box>
  );
}
