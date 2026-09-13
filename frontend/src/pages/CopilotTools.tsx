/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Paper,
  Typography,
} from "@mui/material";
import BuildIcon from "@mui/icons-material/Build";
import SecurityIcon from "@mui/icons-material/Security";
import { rget } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CopilotTool {
  name: string;
  description: string;
  risk_level: string;
}

/* ------------------------------------------------------------------ */
/*  Risk Level Helpers                                                 */
/* ------------------------------------------------------------------ */

function RiskChip({ level }: { level: string }) {
  const colorMap: Record<string, "success" | "warning" | "error" | "default"> = {
    low: "success",
    medium: "warning",
    high: "error",
  };
  return (
    <Chip
      label={level}
      size="small"
      color={colorMap[level] || "default"}
      variant="outlined"
      icon={<SecurityIcon />}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function CopilotTools() {
  const [tools, setTools] = useState<CopilotTool[]>([]);
  const [error, setError] = useState("");

  const loadTools = useCallback(() => {
    rget<{ data: CopilotTool[] }>("/copilot/tools")
      .then((res) => setTools(res.data || []))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadTools();
  }, [loadTools]);

  const totalTools = tools.length;
  const lowRisk = tools.filter((t) => t.risk_level === "low").length;
  const mediumRisk = tools.filter((t) => t.risk_level === "medium").length;
  const highRisk = tools.filter((t) => t.risk_level === "high").length;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Copilot Tools
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Available tools and their capabilities for the BI Copilot
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "primary.main" }}>
                {totalTools}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Tools
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "success.main" }}>
                {lowRisk}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Low Risk
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "warning.main" }}>
                {mediumRisk}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Medium Risk
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: "error.main" }}>
                {highRisk}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                High Risk
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tool Cards */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        Tool Details
      </Typography>
      <Grid container spacing={2}>
        {tools.map((tool) => (
          <Grid key={tool.name} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                  <BuildIcon color="primary" />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
                    {tool.name}
                  </Typography>
                  <RiskChip level={tool.risk_level} />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {tool.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {tools.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Paper sx={{ p: 3, textAlign: "center" }}>
              <Typography color="text.secondary">No tools available</Typography>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
