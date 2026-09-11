/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { rget, rpost } from "../api";

interface Template {
  name: string; description: string; category: string; tags: string[];
}

export function WorkflowTemplates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(() => {
    rget<{ templates: Template[] }>("/workflows/templates/list")
      .then((res) => setTemplates(res.templates || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleUseTemplate = async (template: Template) => {
    try {
      const res = await rpost<any>("/workflows", {
        name: template.name,
        description: template.description,
        trigger: { type: "manual" },
        steps: [],
        conditions: [],
        tags: template.tags || [],
      });
      if (res.success) {
        setSuccess(`Template "${template.name}" created as a new draft workflow`);
        setTimeout(() => window.location.href = `/workflows/${res.workflow_id}`, 1500);
      }
    } catch (e: any) { setError(e.message); }
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}><CircularProgress /></Box>;

  const categories = [...new Set(templates.map((t) => t.category || "general"))];

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>Workflow Templates</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Start from a pre-built template to quickly create automated workflows
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>{success}</Alert>}

      {categories.map((cat) => (
        <Box key={cat} sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2, textTransform: "capitalize" }}>{cat}</Typography>
          <Grid container spacing={2}>
            {templates.filter((t) => (t.category || "general") === cat).map((t) => (
              <Grid key={t.name} size={{ xs: 12, sm: 6, md: 4 }}>
                <Card sx={{ height: "100%" }}>
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>{t.name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t.description}</Typography>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mb: 2 }}>
                      {(t.tags || []).map((tag) => <Chip key={tag} label={tag} size="small" variant="outlined" />)}
                    </Box>
                    <Button variant="outlined" size="small" startIcon={<AddIcon />}
                      onClick={() => handleUseTemplate(t)} fullWidth>
                      Use Template
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}
    </Box>
  );
}
