import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Paper,
  TextField,
  Typography,
} from "@mui/material";

export function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError("");
    if (!email.trim() || !password) {
      setError("Email and password are required");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(
          data.detail === "Invalid email or password"
            ? "Invalid email or password"
            : `Login failed (${res.status})`,
        );
        return;
      }
      if (!data.access_token) {
        setError("Login response did not include a token");
        return;
      }
      localStorage.setItem("bi_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("bi_refresh_token", data.refresh_token);
      navigate("/", { replace: true });
    } catch {
      setError("Could not reach the server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Paper sx={{ p: 4, width: 400, maxWidth: "90vw" }}>
        <Typography variant="h5" gutterBottom>
          BI Platform
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Sign in to continue
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          />
          <Button
            variant="contained"
            onClick={handleLogin}
            disabled={loading}
            fullWidth
          >
            {loading ? "Signing in..." : "Sign in"}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
