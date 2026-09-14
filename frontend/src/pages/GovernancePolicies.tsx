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
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Switch,
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
import DeleteIcon from "@mui/icons-material/Delete";
import ToggleOnIcon from "@mui/icons-material/ToggleOn";
import ToggleOffIcon from "@mui/icons-material/ToggleOff";
import RefreshIcon from "@mui/icons-material/Refresh";
import { rget, rpost, rdel, rpatch } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Policy {
  id: string;
  name: string;
  description: string;
  resource_type: string;
  action: string;
  effect: string;
  conditions: Record<string, any> | null;
  priority: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function GovernancePolicies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    resource_type: "dashboard",
    action: "read",
    effect: "allow",
    priority: 0,
    enabled: true,
  });

  const fetchPolicies = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<{ policies: Policy[] }>("/governance/policies");
      setPolicies(res.policies || []);
    } catch (e: any) {
      setError(e.message || "Failed to load policies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    setError("");
    try {
      await rpost("/governance/policies", form);
      setDialogOpen(false);
      setForm({ name: "", description: "", resource_type: "dashboard", action: "read", effect: "allow", priority: 0, enabled: true });
      await fetchPolicies();
    } catch (e: any) {
      setError(e.message || "Failed to create policy");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (policy: Policy) => {
    try {
      await rpatch(`/governance/policies/${policy.id}`, { enabled: !policy.enabled });
      await fetchPolicies();
    } catch (e: any) {
      setError(e.message || "Failed to toggle policy");
    }
  };

  const handleDelete = async (policyId: string) => {
    if (!confirm("Delete this policy?")) return;
    try {
      await rdel(`/governance/policies/${policyId}`);
      await fetchPolicies();
    } catch (e: any) {
      setError(e.message || "Failed to delete policy");
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>Policies</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchPolicies} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            Create Policy
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
      ) : policies.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Resource</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Effect</TableCell>
                <TableCell>Enabled</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Updated</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {policies.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{p.name}</Typography>
                  </TableCell>
                  <TableCell><Chip label={p.resource_type} size="small" variant="outlined" /></TableCell>
                  <TableCell><Chip label={p.action} size="small" variant="outlined" /></TableCell>
                  <TableCell>
                    <Chip
                      label={p.effect}
                      size="small"
                      color={p.effect === "allow" ? "success" : "error"}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={p.enabled ? "Enabled" : "Disabled"}
                      size="small"
                      color={p.enabled ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell>{p.priority}</TableCell>
                  <TableCell>{p.updated_at ? new Date(p.updated_at).toLocaleDateString() : "-"}</TableCell>
                  <TableCell align="center">
                    <Tooltip title={p.enabled ? "Disable" : "Enable"}>
                      <IconButton size="small" onClick={() => handleToggle(p)}>
                        {p.enabled ? <ToggleOnIcon fontSize="small" color="success" /> : <ToggleOffIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" onClick={() => handleDelete(p.id)} color="error">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Policy Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Policy</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <TextField
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            fullWidth
            multiline
            rows={3}
          />
          <FormControl fullWidth>
            <InputLabel>Resource</InputLabel>
            <Select
              value={form.resource_type}
              label="Resource"
              onChange={(e) => setForm({ ...form, resource_type: e.target.value })}
            >
              <MenuItem value="dashboard">Dashboard</MenuItem>
              <MenuItem value="report">Report</MenuItem>
              <MenuItem value="dataset">Dataset</MenuItem>
              <MenuItem value="model">Model</MenuItem>
              <MenuItem value="pipeline">Pipeline</MenuItem>
              <MenuItem value="user">User</MenuItem>
              <MenuItem value="organization">Organization</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Action</InputLabel>
            <Select
              value={form.action}
              label="Action"
              onChange={(e) => setForm({ ...form, action: e.target.value })}
            >
              <MenuItem value="read">Read</MenuItem>
              <MenuItem value="write">Write</MenuItem>
              <MenuItem value="delete">Delete</MenuItem>
              <MenuItem value="share">Share</MenuItem>
              <MenuItem value="export">Export</MenuItem>
              <MenuItem value="execute">Execute</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Effect</InputLabel>
            <Select
              value={form.effect}
              label="Effect"
              onChange={(e) => setForm({ ...form, effect: e.target.value })}
            >
              <MenuItem value="allow">Allow</MenuItem>
              <MenuItem value="deny">Deny</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Priority"
            type="number"
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 0 })}
            fullWidth
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.enabled}
                onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
              />
            }
            label="Enabled"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={!form.name.trim() || creating}>
            {creating ? <CircularProgress size={20} /> : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
