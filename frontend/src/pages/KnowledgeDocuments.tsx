/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  IconButton,
  MenuItem,
  Paper,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import RefreshIcon from "@mui/icons-material/Refresh";
import VisibilityIcon from "@mui/icons-material/Visibility";
import ReplayIcon from "@mui/icons-material/Replay";
import DeleteIcon from "@mui/icons-material/Delete";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { rget, rdel } from "../api";
import { useMutation } from "../components";
import { Loading, ErrorBanner, NoticeBanner, EmptyState, ConfirmDialog } from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface KnowledgeDocument {
  document_id: string;
  filename: string;
  content_type: string;
  status: string;
  file_size: number;
  chunk_count: number;
  collection_name: string;
  collection_id: string;
  uploaded_by: string;
  created_at: string;
  indexed_at: string | null;
}

interface Collection {
  collection_id: string;
  name: string;
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

export function KnowledgeDocuments() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [collectionFilter, setCollectionFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [totalCount, setTotalCount] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      params.set("page", String(page + 1));
      params.set("pageSize", String(pageSize));
      if (collectionFilter !== "all") params.set("collection_id", collectionFilter);
      if (statusFilter !== "all") params.set("status", statusFilter);

      const res = await rget<{ documents: KnowledgeDocument[]; total: number }>(
        `/knowledge/documents?${params.toString()}`
      );
      setDocuments(res.documents || []);
      setTotalCount(res.total || 0);
    } catch (e: any) {
      setError(e.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, collectionFilter, statusFilter]);

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

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const { run: handleDelete, busy: deleteBusy } = useMutation(
    async (doc: KnowledgeDocument) => {
      await rdel(`/knowledge/documents/${doc.document_id}`);
    },
    () => {
      setNotice("Document deleted successfully");
      setDeleteTarget(null);
      fetchDocuments();
    }
  );

  const handleReindex = async (doc: KnowledgeDocument) => {
    try {
      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch(`/api/v1/knowledge/documents/${doc.document_id}/reindex`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) throw new Error("Reindex failed");
      setNotice("Document reindexing started");
      fetchDocuments();
    } catch (e: any) {
      setError(e.message || "Reindex failed");
    }
  };

  const columns: GridColDef[] = [
    {
      field: "filename",
      headerName: "Filename",
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {params.value}
        </Typography>
      ),
    },
    { field: "content_type", headerName: "Type", width: 100 },
    {
      field: "collection_name",
      headerName: "Collection",
      width: 140,
      renderCell: (params) => params.value || "-",
    },
    {
      field: "status",
      headerName: "Status",
      width: 120,
      renderCell: (params) => <StatusChip status={params.value} />,
    },
    {
      field: "file_size",
      headerName: "Size",
      width: 100,
      renderCell: (params) => formatFileSize(params.value),
    },
    { field: "chunk_count", headerName: "Chunks", width: 80 },
    { field: "uploaded_by", headerName: "Uploaded By", width: 120 },
    {
      field: "created_at",
      headerName: "Uploaded",
      width: 160,
      renderCell: (params) => new Date(params.value).toLocaleString(),
    },
    {
      field: "indexed_at",
      headerName: "Indexed",
      width: 160,
      renderCell: (params) => (params.value ? new Date(params.value).toLocaleString() : "-"),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 150,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const doc = params.row as KnowledgeDocument;
        return (
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <Tooltip title="View details">
              <IconButton
                size="small"
                onClick={() => {
                  window.location.href = `/knowledge/documents/${doc.document_id}`;
                }}
              >
                <VisibilityIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Reindex">
              <IconButton size="small" onClick={() => handleReindex(doc)}>
                <ReplayIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton size="small" color="error" onClick={() => setDeleteTarget(doc)}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        );
      },
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Documents</Typography>
        <Button
          variant="contained"
          startIcon={<CloudUploadIcon />}
          onClick={() => {
            window.location.href = "/knowledge/upload";
          }}
        >
          Upload
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage and search through your knowledge base documents
      </Typography>

      <ErrorBanner error={error} />
      <NoticeBanner notice={notice} />

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
          <TextField
            select
            size="small"
            label="Collection"
            value={collectionFilter}
            onChange={(e) => {
              setCollectionFilter(e.target.value);
              setPage(0);
            }}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 180 }}
          >
            <MenuItem value="all">All Collections</MenuItem>
            {collections.map((c) => (
              <MenuItem key={c.collection_id} value={c.collection_id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            size="small"
            label="Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 140 }}
          >
            <MenuItem value="all">All Statuses</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="processing">Processing</MenuItem>
            <MenuItem value="indexed">Indexed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </TextField>

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title="Refresh">
            <IconButton onClick={fetchDocuments} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Paper>

      {/* DataGrid */}
      <Paper sx={{ height: 600 }}>
        <DataGrid
          rows={documents}
          columns={columns}
          getRowId={(row) => row.document_id}
          loading={loading}
          paginationMode="server"
          rowCount={totalCount}
          paginationModel={{ page, pageSize }}
          onPaginationModelChange={(model) => {
            setPage(model.page);
            setPageSize(model.pageSize);
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          disableRowSelectionOnClick
          sx={{
            border: 0,
            "& .MuiDataGrid-cell": { py: 1 },
          }}
        />
      </Paper>

      {/* Empty state */}
      {!loading && documents.length === 0 && (
        <Box sx={{ mt: 2 }}>
          <EmptyState message="No documents found. Upload your first document to get started." />
        </Box>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Document"
        message={`Are you sure you want to delete "${deleteTarget?.filename}"? This will also remove all associated chunks and cannot be undone.`}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && handleDelete(deleteTarget)}
      />
    </Box>
  );
}
