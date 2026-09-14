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
  Grid,
  IconButton,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { rget } from "../api";
import { GovernancePolicies } from "./GovernancePolicies";
import { GovernanceClassifications } from "./GovernanceClassifications";
import { GovernanceSecurity } from "./GovernanceSecurity";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface OverviewData {
  total_policies: number;
  enabled_policies: number;
  total_classifications: number;
  total_security_events: number;
  unresolved_events: number;
  total_shares: number;
  total_access_reviews: number;
  pending_reviews: number;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function Governance() {
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState<OverviewData | null>(null);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await rget<OverviewData>("/governance/overview");
      setOverview(res);
    } catch (e: any) {
      setError(e.message || "Failed to load governance overview");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const tabLabels = ["Overview", "Policies", "Classifications", "Security Events"];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="h4">Governance</Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchOverview} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage data governance policies, classifications, security events, and access reviews
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        {tabLabels.map((label) => (
          <Tab key={label} label={label} />
        ))}
      </Tabs>

      {loading && <CircularProgress />}

      {/* Overview Tab */}
      {!loading && tab === 0 && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Total Policies</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_policies ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Enabled Policies</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.enabled_policies ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Classifications</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_classifications ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Security Events</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_security_events ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Unresolved Events</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, color: (overview?.unresolved_events ?? 0) > 0 ? "error.main" : "inherit" }}>
                    {overview?.unresolved_events ?? 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Share Permissions</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_shares ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Access Reviews</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600 }}>{overview?.total_access_reviews ?? 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">Pending Reviews</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 600, color: (overview?.pending_reviews ?? 0) > 0 ? "warning.main" : "inherit" }}>
                    {overview?.pending_reviews ?? 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {!overview && <Paper sx={{ p: 4, textAlign: "center" }}><Typography color="text.secondary">No data available yet.</Typography></Paper>}
        </>
      )}

      {!loading && tab === 1 && <GovernancePolicies />}
      {!loading && tab === 2 && <GovernanceClassifications />}
      {!loading && tab === 3 && <GovernanceSecurity />}
    </Box>
  );
}
