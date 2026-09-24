import { useState, useEffect } from "react";
import { Box, Typography, Paper, Grid, Chip, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Alert } from "@mui/material";
import { rget, rpatch } from "../api";

interface TenantInfo {
  id: string;
  name: string;
  slug: string;
  status: string;
  plan: string;
  created_at: string;
  plan_details: any;
}

export function TenantOrganization() {
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchTenant();
  }, []);

  const fetchTenant = async () => {
    try {
      const data = await rget<TenantInfo>("/tenant/current");
      setTenant(data);
      setEditName(data.name);
    } catch {
      setMessage("Failed to load organization");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    try {
      await rpatch("/tenant/current", { name: editName });
      setMessage("Organization updated");
      setEditOpen(false);
      fetchTenant();
    } catch {
      setMessage("Failed to update");
    }
  };

  if (loading) return <Box sx={{ p: 3 }}><Typography>Loading...</Typography></Box>;
  if (!tenant) return <Box sx={{ p: 3 }}><Alert severity="error">Organization not found</Alert></Box>;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Organization</Typography>
      {message && <Alert severity="info" sx={{ mb: 2 }} onClose={() => setMessage("")}>{message}</Alert>}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Details</Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <Box><Typography variant="body2" color="text.secondary">Name</Typography><Typography>{tenant.name}</Typography></Box>
              <Box><Typography variant="body2" color="text.secondary">Slug</Typography><Typography>{tenant.slug}</Typography></Box>
              <Box><Typography variant="body2" color="text.secondary">Status</Typography><Chip label={tenant.status} color={tenant.status === "active" ? "success" : "warning"} size="small" /></Box>
              <Box><Typography variant="body2" color="text.secondary">Plan</Typography><Chip label={tenant.plan} color="primary" size="small" /></Box>
              <Box><Typography variant="body2" color="text.secondary">Created</Typography><Typography>{new Date(tenant.created_at).toLocaleDateString()}</Typography></Box>
            </Box>
            <Button variant="outlined" sx={{ mt: 2 }} onClick={() => setEditOpen(true)}>Edit</Button>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Plan Limits</Typography>
            {tenant.plan_details && (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <Box><Typography variant="body2">Max Users: {tenant.plan_details.max_users}</Typography></Box>
                <Box><Typography variant="body2">Max Datasets: {tenant.plan_details.max_datasets}</Typography></Box>
                <Box><Typography variant="body2">Max Storage: {tenant.plan_details.max_storage_mb} MB</Typography></Box>
                <Box><Typography variant="body2">Max AI Requests: {tenant.plan_details.max_ai_requests}</Typography></Box>
                <Box><Typography variant="body2">Max Dashboards: {tenant.plan_details.max_dashboards}</Typography></Box>
                <Box><Typography variant="body2">Max Workflows: {tenant.plan_details.max_workflows}</Typography></Box>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
      <Dialog open={editOpen} onClose={() => setEditOpen(false)}>
        <DialogTitle>Edit Organization</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Name" value={editName} onChange={(e) => setEditName(e.target.value)} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdate} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
