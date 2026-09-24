import { useState, useEffect } from "react";
import { Box, Typography, Paper, Grid, LinearProgress, Alert } from "@mui/material";
import { rget } from "../api";

interface QuotaInfo {
  limit: number;
  current: number;
  remaining: number;
  percentage: number;
}

interface QuotasResponse {
  plan: string;
  quotas: Record<string, QuotaInfo>;
}

const resourceLabels: Record<string, string> = {
  users: "Users",
  datasets: "Datasets",
  storage_mb: "Storage (MB)",
  ai_requests: "AI Requests",
  ai_tokens: "AI Tokens",
  queries: "Queries",
  reports: "Reports",
  dashboards: "Dashboards",
  workflows: "Workflows",
  rag_documents: "RAG Documents",
  rag_storage_mb: "RAG Storage (MB)",
  predictions: "Predictions",
  api_keys: "API Keys",
};

export function TenantUsage() {
  const [quotas, setQuotas] = useState<QuotasResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchQuotas();
  }, []);

  const fetchQuotas = async () => {
    try {
      const data = await rget<QuotasResponse>("/tenant/quotas");
      setQuotas(data);
    } catch {
      setError("Failed to load usage data");
    } finally {
      setLoading(false);
    }
  };

  const getColour = (pct: number) => (pct >= 90 ? "error" : pct >= 70 ? "warning" : "primary");

  if (loading) return <Box sx={{ p: 3 }}><Typography>Loading...</Typography></Box>;
  if (error) return <Box sx={{ p: 3 }}><Alert severity="error">{error}</Alert></Box>;
  if (!quotas) return null;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>Usage & Quotas</Typography>
      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 3 }}>Plan: {quotas.plan}</Typography>
      <Grid container spacing={2}>
        {Object.entries(quotas.quotas).map(([key, q]) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={key}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="body2" color="text.secondary">{resourceLabels[key] || key}</Typography>
              <Typography variant="h6">{q.current} / {q.limit}</Typography>
              <LinearProgress variant="determinate" value={Math.min(q.percentage, 100)} color={getColour(q.percentage)} sx={{ mt: 1 }} />
              <Typography variant="caption" color="text.secondary">{q.remaining} remaining ({q.percentage}%)</Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
