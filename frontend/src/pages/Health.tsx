import { useState } from "react";
import { Box, Button, Card, CardContent, Chip, Grid, Typography } from "@mui/material";
import { get } from "../api";
import { ErrorBanner, Loading, useFetch } from "../components";

function statusColor(status: string) {
  if (status === "ok") return "success";
  if (status === "degraded" || status === "warning") return "warning";
  return "error";
}

export function Health() {
  const [tick, setTick] = useState(0);
  const [auto, setAuto] = useState(false);
  const { data, error, loading } = useFetch(() => get<any>("/health"), [tick, auto]);

  useFetch(async () => {
    if (!auto) return null;
    await new Promise((r) => setTimeout(r, 5000));
    setTick((t) => t + 1);
    return null;
  }, [tick, auto]);

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h4">
          Health — overall: <Chip label={data.overall} color={statusColor(data.overall)} />
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button variant={auto ? "contained" : "outlined"} onClick={() => setAuto(!auto)}>
            Auto-refresh {auto ? "on" : "off"}
          </Button>
          <Button variant="outlined" onClick={() => setTick((t) => t + 1)}>
            Refresh
          </Button>
        </Box>
      </Box>
      <Grid container spacing={2}>
        {(data.services ?? []).map((s: any) => (
          <Grid size={{ xs: 12, md: 6, lg: 4 }} key={s.service}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="h6" sx={{ textTransform: "capitalize" }}>
                    {s.service}
                  </Typography>
                  <Chip label={s.status} color={statusColor(s.status)} size="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Latency: {s.latency_ms} ms
                </Typography>
                <Typography variant="body2">{s.detail}</Typography>
                {Object.entries(s)
                  .filter(([k]) => !["service", "status", "latency_ms", "detail"].includes(k))
                  .map(([k, v]) => (
                    <Typography key={k} variant="body2" color="text.secondary">
                      {k}: {String(v)}
                    </Typography>
                  ))}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </>
  );
}
