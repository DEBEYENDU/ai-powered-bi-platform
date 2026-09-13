/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import DeleteIcon from "@mui/icons-material/Delete";
import { rget, rpost, rdel } from "../api";
import { useMutation } from "../components";
import {
  Loading,
  ErrorBanner,
  NoticeBanner,
  EmptyState,
  ConfirmDialog,
  FormDialog,
  Field,
} from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Collection {
  collection_id: string;
  name: string;
  description: string;
  access_policy: string;
  document_count: number;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function KnowledgeCollections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newAccessPolicy, setNewAccessPolicy] = useState("private");
  const [deleteTarget, setDeleteTarget] = useState<Collection | null>(null);

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ collections: Collection[] }>("/knowledge/collections");
      setCollections(res.collections || []);
    } catch (e: any) {
      setError(e.message || "Failed to load collections");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const { run: handleCreate, busy: createBusy } = useMutation(
    async () => {
      await rpost("/knowledge/collections", {
        name: newName,
        description: newDescription,
        access_policy: newAccessPolicy,
      });
    },
    () => {
      setNotice("Collection created successfully");
      setCreateOpen(false);
      setNewName("");
      setNewDescription("");
      setNewAccessPolicy("private");
      fetchCollections();
    }
  );

  const { run: handleDelete, busy: deleteBusy } = useMutation(
    async (coll: Collection) => {
      await rdel(`/knowledge/collections/${coll.collection_id}`);
    },
    () => {
      setNotice("Collection deleted successfully");
      setDeleteTarget(null);
      fetchCollections();
    }
  );

  const handleSubmitCreate = () => {
    if (!newName.trim()) return;
    handleCreate(undefined as any);
  };

  if (loading) return <Loading />;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Collections</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateOpen(true)}
        >
          Create Collection
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Organize documents into collections for targeted retrieval
      </Typography>

      <ErrorBanner error={error} />
      <NoticeBanner notice={notice} />

      {collections.length === 0 ? (
        <Paper sx={{ p: 4 }}>
          <EmptyState message="No collections created yet. Create your first collection to organize documents." />
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {collections.map((coll) => (
            <Grid key={coll.collection_id} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card
                sx={{
                  cursor: "pointer",
                  transition: "all 0.2s",
                  "&:hover": { borderColor: "primary.main", borderWidth: 1, borderStyle: "solid" },
                }}
                onClick={() => {
                  window.location.href = `/knowledge/collections/${coll.collection_id}`;
                }}
              >
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                      <LibraryBooksIcon color="primary" />
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {coll.name}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      color="error"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(coll);
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </Button>
                  </Box>

                  {coll.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {coll.description}
                    </Typography>
                  )}

                  <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                    <Chip
                      label={`${coll.document_count} document${coll.document_count !== 1 ? "s" : ""}`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={coll.access_policy}
                      size="small"
                      variant="outlined"
                      color={coll.access_policy === "public" ? "primary" : "default"}
                    />
                  </Box>

                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                    Created: {new Date(coll.created_at).toLocaleDateString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Collection Dialog */}
      <FormDialog
        open={createOpen}
        title="Create Collection"
        onClose={() => setCreateOpen(false)}
        onSubmit={handleSubmitCreate}
        submitLabel={createBusy ? "Creating..." : "Create"}
      >
        <TextField
          fullWidth
          size="small"
          label="Collection Name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          required
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          fullWidth
          size="small"
          label="Description"
          value={newDescription}
          onChange={(e) => setNewDescription(e.target.value)}
          multiline
          rows={3}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          select
          fullWidth
          size="small"
          label="Access Policy"
          value={newAccessPolicy}
          onChange={(e) => setNewAccessPolicy(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        >
          <MenuItem value="private">Private</MenuItem>
          <MenuItem value="team">Team</MenuItem>
          <MenuItem value="public">Public</MenuItem>
        </TextField>
      </FormDialog>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Collection"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? Documents in this collection will not be deleted, but they will be moved to the default collection.`}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && handleDelete(deleteTarget)}
      />
    </Box>
  );
}
