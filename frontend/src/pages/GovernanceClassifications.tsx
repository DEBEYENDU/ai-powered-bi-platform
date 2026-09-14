/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  IconButton,
  InputLabel,
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
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import RefreshIcon from "@mui/icons-material/Refresh";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Classification {
  id: string;
  resource_type: string;
  resource_id: string;
  classification: string;
  sensitivity_tags: string[];
  classified_by: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const classificationColor: Record<string, "default" | "success" | "warning" | "error" | "info" | "primary"> = {
  public: "success",
  internal: "info",
  confidential: "warning",
  restricted: "error",
  secret: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function GovernanceClassifications() {
  const [classifications, setClassifications] = useState<Classification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    resource_type: "dashboard",
    resource_id: "",
    classification: "internal",
    sensitivity_tags: "",
    notes: "",
  });

  const fetchClassifications = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ classifications: Classification[] }>("/governance/classifications");
      setClassifications(res.classifications || []);
    } catch (e: any) {
      setError(e.message || "Failed to load classifications");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClassifications();
  }, [fetchClassifications]);

  const handleCreate = async () => {
    if (!form.resource_id.trim()) return;
    setCreating(true);
    setError("");
    try {
      const payload = {
        ...form,
        sensitivity_tags: form.sensitivity_tags
          ? form.sensitivity_tags.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
      };
      await rpost("/governance/classifications", payload);
      setDialogOpen(false);
      setForm({ resource_type: "dashboard", resource_id: "", classification: "internal", sensitivity_tags: "", notes: "" });
      await fetchClassifications();
    } catch (e: any) {
      setError(e.message || "Failed to create classification");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>Classifications</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchClassifications} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Classify Resource
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CircularProgress />
      ) : classifications.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Resource Type</TableCell>
                <TableCell>Resource ID</TableCell>
                <TableCell>Classification</TableCell>
                <TableCell>Sensitivity Tags</TableCell>
                <TableCell>Classified By</TableCell>
                <TableCell>Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {classifications.map((c) => (
                <TableRow key={c.id} hover>
                  <TableCell><Chip label={c.resource_type} size="small" variant="outlined" /></TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                      {c.resource_id.length > 12 ? `${c.resource_id.slice(0, 12)}...` : c.resource_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={c.classification}
                      size="small"
                      color={classificationColor[c.classification] || "default"}
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {c.sensitivity_tags?.map((tag) => (
                        <Chip key={tag} label={tag} size="small" variant="outlined" />
                      )) || "-"}
                    </Box>
                  </TableCell>
                  <TableCell>{c.classified_by || "-"}</TableCell>
                  <TableCell>{c.created_at ? new Date(c.created_at).toLocaleDateString() : "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Classify Resource Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Classify Resource</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <FormControl fullWidth>
            <InputLabel>Resource Type</InputLabel>
            <Select
              value={form.resource_type}
              label="Resource Type"
              onChange={(e) => setForm({ ...form, resource_type: e.target.value })}
            >
              <MenuItem value="dashboard">Dashboard</MenuItem>
              <MenuItem value="report">Report</MenuItem>
              <MenuItem value="dataset">Dataset</MenuItem>
              <MenuItem value="model">Model</MenuItem>
              <MenuItem value="pipeline">Pipeline</MenuItem>
              <MenuItem value="document">Document</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Resource ID"
            value={form.resource_id}
            onChange={(e) => setForm({ ...form, resource_id: e.target.value })}
            fullWidth
            required
          />
          <FormControl fullWidth>
            <InputLabel>Classification</InputLabel>
            <Select
              value={form.classification}
              label="Classification"
              onChange={(e) => setForm({ ...form, classification: e.target.value })}
            >
              <MenuItem value="public">Public</MenuItem>
              <MenuItem value="internal">Internal</MenuItem>
              <MenuItem value="confidential">Confidential</MenuItem>
              <MenuItem value="restricted">Restricted</MenuItem>
              <MenuItem value="secret">Secret</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Sensitivity Tags (comma-separated)"
            value={form.sensitivity_tags}
            onChange={(e) => setForm({ ...form, sensitivity_tags: e.target.value })}
            fullWidth
            placeholder="e.g. pii, financial, health"
          />
          <TextField
            label="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            fullWidth
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!form.resource_id.trim() || creating}>
            {creating ? <CircularProgress size={20} /> : "Classify"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
