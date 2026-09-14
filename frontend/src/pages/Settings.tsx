import { useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, MenuItem, TextField, Typography } from "@mui/material";
import { get, patch, post } from "../api";
import { ErrorBanner, Field, Loading, NoticeBanner, useFetch, useMutation } from "../components";

export function Settings() {
  const { data, error, loading, setData } = useFetch(() => get<any>("/settings"));
  const {
    data: maint,
    error: maintError,
    loading: maintLoading,
  } = useFetch(() => get<any>("/maintenance"));
  const [mode, setMode] = useState("off");
  const [editKey, setEditKey] = useState("");
  const [editValue, setEditValue] = useState("");
  const [confirm, setConfirm] = useState<string | null>(null);
  const mutation = useMutation(
    async (fn: () => Promise<unknown>) => {
      await fn();
      setData(await get<any>("/settings"));
    }
  );

  if (loading || maintLoading) return <Loading />;
  if (error || !data) return <ErrorBanner error={error ?? "No data"} />;
  if (maintError || !maint) return <ErrorBanner error={maintError ?? "No data"} />;
  const currentMode = maint.mode as string;
  const isWriteBlocked = maint.is_write_blocked as boolean;

  async function applyMaintenance() {
    await mutation.run(
      () => post<any>("/maintenance", { mode }),
      `Maintenance mode is now "${mode}".`
    );
  }
  async function saveSetting() {
    let value: unknown = editValue;
    try {
      value = JSON.parse(editValue);
    } catch {
      /* keep as string */
    }
    await mutation.run(
      () => patch(`/settings/${editKey}`, { value: { value } }),
      `Setting ${editKey} updated.`
    );
  }

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <ErrorBanner error={mutation.error} />
      <NoticeBanner notice={mutation.notice} />
      {isWriteBlocked && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Platform is currently in <strong>{currentMode.toUpperCase()}</strong> mode. Organization and user creation are disabled. Only GET requests are allowed.
          Set maintenance mode to "off" via the control below to restore write access.
        </Alert>
      )}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Maintenance mode
          </Typography>
          <Typography gutterBottom>
            Current status:{" "}
            <Chip
              label={currentMode === "off" ? "INACTIVE" : currentMode.toUpperCase()}
              color={currentMode === "off" ? "success" : currentMode === "readonly" ? "warning" : "error"}
            />
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {currentMode === "off"
              ? "All read and write operations are allowed."
              : currentMode === "readonly"
                ? "Only read (GET/HEAD/OPTIONS) operations are allowed. All writes return 503."
                : "All requests are blocked except /health, /docs, and maintenance endpoints."}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
            <TextField
              select
              label="New mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              size="small"
              sx={{ minWidth: 200 }}
            >
              <MenuItem value="off">off</MenuItem>
              <MenuItem value="readonly">readonly</MenuItem>
              <MenuItem value="maintenance">maintenance</MenuItem>
            </TextField>
            <Button
              variant="contained"
              onClick={() => {
                if (mode !== "off" && mode !== currentMode) {
                  setConfirm(mode);
                } else {
                  applyMaintenance();
                }
              }}
            >
              Apply
            </Button>
          </Box>
          {confirm && (
            <Box sx={{ mt: 1 }}>
              <Alert severity="warning">
                Switch from "{currentMode}" to "{confirm}"?{" "}
                {confirm !== "off" && "Writes will return 503 until you switch back."}
              </Alert>
              <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                <Button
                  color={confirm === "off" ? "primary" : "error"}
                  variant="contained"
                  onClick={() => {
                    applyMaintenance();
                    setConfirm(null);
                  }}
                >
                  Confirm
                </Button>
                <Button onClick={() => setConfirm(null)}>Cancel</Button>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            System settings
          </Typography>
          <pre>{JSON.stringify(data, null, 2)}</pre>
          <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
            <TextField label="Key" value={editKey} onChange={(e) => setEditKey(e.target.value)} size="small" />
            <TextField
              label='Value (JSON, e.g. "INFO" or 120)'
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              size="small"
              sx={{ minWidth: 280 }}
            />
            <Button variant="outlined" onClick={saveSetting}>
              Save
            </Button>
          </Box>
        </CardContent>
      </Card>
    </>
  );
}
