import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Alert,
  AppBar,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { useColorMode } from "./theme";

const NAV: Array<[string, string]> = [
  ["Overview", "/"],
  ["Users", "/users"],
  ["Organizations", "/orgs"],
  ["Roles", "/roles"],
  ["Dashboards", "/dashboards"],
  ["Reports", "/reports"],
  ["AI Admin", "/ai"],
  ["AI Chat", "/ai/chat"],
  ["Ask Your Data", "/ai/ask"],
  ["AI Dashboard Gen", "/ai/dashboard-gen"],
  ["Business Insights", "/ai/insights"],
  ["AI Reports", "/ai/reports"],
  ["Data Sources", "/de/sources"],
  ["Data Quality", "/de/quality"],
  ["Data Cleaning", "/de/cleaning"],
  ["Transform Builder", "/de/transform"],
  ["Pipelines", "/de/pipelines"],
  ["Forecasting", "/pred/forecast"],
  ["Model Management", "/pred/models"],
  ["Scenario Analysis", "/pred/scenarios"],
  ["Model Performance", "/pred/performance"],
  ["Workflows", "/workflows"],
  ["Workflow Builder", "/workflows/builder"],
  ["Workflow Templates", "/workflows/templates"],
  ["Approvals", "/workflows/approvals"],
  ["Agent Dashboard", "/agents"],
  ["Agent Status", "/agents/status"],
  ["Task History", "/agents/history"],
  ["Execution Graph", "/agents/graph"],
  ["Agent Logs", "/agents/logs"],
  ["Memory Viewer", "/agents/memory"],
  ["Health", "/health"],
  ["Metrics", "/metrics"],
  ["Audit", "/audit"],
  ["Alerts", "/alerts"],
  ["Jobs", "/jobs"],
  ["Flags", "/flags"],
  ["Settings", "/settings"],
];

const DRAWER_WIDTH = 220;

export function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { toggle, mode } = useColorMode();
  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography
            variant="h6"
            sx={{ flexGrow: 1, cursor: "pointer" }}
            onClick={() => navigate("/")}
          >
            BI Platform Admin
          </Typography>
          <IconButton color="inherit" onClick={toggle} aria-label="toggle theme">
            {mode === "dark" ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <List>
          {NAV.map(([label, to]) => (
            <ListItem key={to + label} disablePadding>
              <ListItemButton component={Link} to={to} selected={pathname === to}>
                <ListItemText primary={label} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}

export function useFetch<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true);
    fn()
      .then((d) => live && setData(d))
      .catch((e) => live && setError(String(e)))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error, loading, setData };
}

/** Mutation helper: runs async work, surfaces backend errors, shows notices. */
export function useMutation<T>(fn: (args: T) => Promise<unknown>, onDone?: () => void) {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function run(args: T, successMessage?: string) {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      await fn(args);
      if (successMessage) setNotice(successMessage);
      onDone?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return { run, error, notice, busy };
}

export function Loading() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
      <CircularProgress />
    </Box>
  );
}

export function ErrorBanner({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      {error}
    </Alert>
  );
}

export function NoticeBanner({ notice }: { notice: string | null }) {
  if (!notice) return null;
  return (
    <Alert severity="success" sx={{ mb: 2 }}>
      {notice}
    </Alert>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <Box sx={{ p: 4, textAlign: "center", color: "text.secondary" }}>
      <Typography>{message}</Typography>
    </Box>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  message: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onClose={onCancel}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={onConfirm} color="error" variant="contained">
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function FormDialog({
  open,
  title,
  onClose,
  onSubmit,
  children,
  submitLabel = "Save",
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  onSubmit: () => void;
  children: ReactNode;
  submitLabel?: string;
}) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>{children}</Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onSubmit} variant="contained">
          {submitLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <TextField
      label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      type={type}
      required={required}
      fullWidth
      size="small"
    />
  );
}
