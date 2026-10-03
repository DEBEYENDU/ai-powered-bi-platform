import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Link,
  Paper,
  TextField,
  Typography,
} from "@mui/material";

type Mode = "login" | "register";

export function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError("");
    setInfo("");
  };

  const handleLogin = async () => {
    setError("");
    setInfo("");
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

  const handleRegister = async () => {
    setError("");
    setInfo("");
    if (!email.trim() || !password) {
      setError("Email and password are required");
      return;
    }
    if (password.length < 12) {
      setError("Password must be at least 12 characters");
      return;
    }
    setLoading(true);
    try {
      const body: Record<string, string> = {
        email: email.trim(),
        password,
      };
      if (fullName.trim()) body.full_name = fullName.trim();
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : null;
        setError(detail ? detail : `Registration failed (${res.status})`);
        return;
      }
      // Auto-login with the new account.
      const loginRes = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const loginData = await loginRes.json().catch(() => ({}));
      if (loginRes.ok && loginData.access_token) {
        localStorage.setItem("bi_token", loginData.access_token);
        if (loginData.refresh_token) {
          localStorage.setItem("bi_refresh_token", loginData.refresh_token);
        }
        navigate("/", { replace: true });
        return;
      }
      setInfo("Account created. Please sign in.");
      setMode("login");
      setPassword("");
    } catch {
      setError("Could not reach the server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => (mode === "login" ? handleLogin() : handleRegister());

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
          {mode === "login"
            ? "Sign in to continue"
            : "Create an account — a workspace is provisioned automatically"}
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {info && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {info}
          </Alert>
        )}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {mode === "register" && (
            <TextField
              label="Full name (optional)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              fullWidth
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          )}
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <TextField
            label={mode === "register" ? "Password (min 12 characters)" : "Password"}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={loading}
            fullWidth
          >
            {loading
              ? mode === "login"
                ? "Signing in..."
                : "Creating account..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </Button>
          {mode === "login" ? (
            <Typography variant="body2" align="center">
              No account?{" "}
              <Link
                component="button"
                type="button"
                onClick={() => switchMode("register")}
                sx={{ cursor: "pointer" }}
              >
                Create one
              </Link>
            </Typography>
          ) : (
            <Typography variant="body2" align="center">
              Already have an account?{" "}
              <Link
                component="button"
                type="button"
                onClick={() => switchMode("login")}
                sx={{ cursor: "pointer" }}
              >
                Sign in
              </Link>
            </Typography>
          )}
        </Box>
      </Paper>
    </Box>
  );
}
