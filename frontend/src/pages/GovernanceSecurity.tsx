/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  Grid,
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
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SecurityEvent {
  id: string;
  event_type: string;
  severity: string;
  resource_type: string;
  resource_id: string;
  user_id: string;
  description: string;
  ip_address: string;
  resolved: boolean;
  resolved_at: string;
  created_at: string;
}

interface SecuritySummary {
  total_events: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  unresolved: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const severityColor: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  info: "info",
  low: "info",
  medium: "warning",
  high: "error",
  critical: "error",
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function GovernanceSecurity() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [checkDialogOpen, setCheckDialogOpen] = useState(false);
  const [checkForm, setCheckForm] = useState({ resource_type: "dashboard", resource_id: "", action: "read" });
  const [checking, setChecking] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (eventTypeFilter) params.set("event_type", eventTypeFilter);
      if (severityFilter) params.set("severity", severityFilter);
      const qs = params.toString() ? `?${params.toString()}` : "";

      const [evRes, sumRes] = await Promise.allSettled([
        rget<{ events: SecurityEvent[] }>(`/governance/security-events${qs}`),
        rget<SecuritySummary>("/governance/security-events/summary"),
      ]);
      if (evRes.status === "fulfilled") setEvents(evRes.value.events || []);
      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
    } catch (e: any) {
      setError(e.message || "Failed to load security events");
    } finally {
      setLoading(false);
    }
  }, [eventTypeFilter, severityFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCheckAuthorization = async () => {
    if (!checkForm.resource_id.trim()) return;
    setChecking(true);
    setError("");
    try {
      const res = await rpost<{ authorized: boolean; reason: string }>("/governance/check-authorization", checkForm);
      setCheckDialogOpen(false);
      alert(res.authorized ? `Authorized: ${res.reason}` : `Denied: ${res.reason}`);
    } catch (e: any) {
      setError(e.message || "Failed to check authorization");
    } finally {
      setChecking(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>Security Events</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="contained" startIcon={<CheckCircleIcon />} onClick={() => setCheckDialogOpen(true)}>
            Check Authorization
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">Total Events</Typography>
                <Typography variant="h4" sx={{ fontWeight: 600 }}>{summary.total_events}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">Unresolved</Typography>
                <Typography variant="h4" sx={{ fontWeight: 600, color: summary.unresolved > 0 ? "error.main" : "inherit" }}>
                  {summary.unresolved}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          {Object.entries(summary.by_severity).map(([sev, count]) => (
            <Grid key={sev} size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">{sev.charAt(0).toUpperCase() + sev.slice(1)}</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, color: `${severityColor[sev] || "info"}.main` }}>{count}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Filters */}
      <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Event Type</InputLabel>
          <Select
            value={eventTypeFilter}
            label="Event Type"
            onChange={(e) => setEventTypeFilter(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="access_denied">Access Denied</MenuItem>
            <MenuItem value="unauthorized_access">Unauthorized Access</MenuItem>
            <MenuItem value="data_export">Data Export</MenuItem>
            <MenuItem value="permission_change">Permission Change</MenuItem>
            <MenuItem value="policy_violation">Policy Violation</MenuItem>
            <MenuItem value="login_failure">Login Failure</MenuItem>
          </Select>
        </FormControl>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Severity</InputLabel>
          <Select
            value={severityFilter}
            label="Severity"
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="info">Info</MenuItem>
            <MenuItem value="low">Low</MenuItem>
            <MenuItem value="medium">Medium</MenuItem>
            <MenuItem value="high">High</MenuItem>
            <MenuItem value="critical">Critical</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Events Table */}
      {loading ? (
        <CircularProgress />
      ) : events.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">No data available yet.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Event Type</TableCell>
                <TableCell>Severity</TableCell>
                <TableCell>Resource</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Resolved</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {events.map((ev) => (
                <TableRow key={ev.id} hover>
                  <TableCell><Chip label={ev.event_type} size="small" variant="outlined" /></TableCell>
                  <TableCell>
                    <Chip label={ev.severity} size="small" color={severityColor[ev.severity] || "default"} />
                  </TableCell>
                  <TableCell>{ev.resource_type ? `${ev.resource_type}/${ev.resource_id || "-"}` : "-"}</TableCell>
                  <TableCell>{ev.description || "-"}</TableCell>
                  <TableCell>{ev.ip_address || "-"}</TableCell>
                  <TableCell>
                    <Chip label={ev.resolved ? "Yes" : "No"} size="small" color={ev.resolved ? "success" : "default"} />
                  </TableCell>
                  <TableCell>{ev.created_at ? new Date(ev.created_at).toLocaleString() : "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Check Authorization Dialog */}
      <Dialog open={checkDialogOpen} onClose={() => setCheckDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Check Authorization</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <FormControl fullWidth>
            <InputLabel>Resource</InputLabel>
            <Select
              value={checkForm.resource_type}
              label="Resource"
              onChange={(e) => setCheckForm({ ...checkForm, resource_type: e.target.value })}
            >
              <MenuItem value="dashboard">Dashboard</MenuItem>
              <MenuItem value="report">Report</MenuItem>
              <MenuItem value="dataset">Dataset</MenuItem>
              <MenuItem value="model">Model</MenuItem>
              <MenuItem value="pipeline">Pipeline</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Resource ID"
            value={checkForm.resource_id}
            onChange={(e) => setCheckForm({ ...checkForm, resource_id: e.target.value })}
            fullWidth
            required
          />
          <FormControl fullWidth>
            <InputLabel>Action</InputLabel>
            <Select
              value={checkForm.action}
              label="Action"
              onChange={(e) => setCheckForm({ ...checkForm, action: e.target.value })}
            >
              <MenuItem value="read">Read</MenuItem>
              <MenuItem value="write">Write</MenuItem>
              <MenuItem value="delete">Delete</MenuItem>
              <MenuItem value="share">Share</MenuItem>
              <MenuItem value="export">Export</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCheckDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCheckAuthorization} disabled={!checkForm.resource_id.trim() || checking}>
            {checking ? <CircularProgress size={20} /> : "Check"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
