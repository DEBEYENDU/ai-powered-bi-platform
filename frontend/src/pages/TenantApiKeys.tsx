import { useState, useEffect } from "react";
import { Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Chip, Alert } from "@mui/material";
import { rget, rpost, rdel } from "../api";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  status: string;
  scopes: string;
  created_at: string;
  last_used_at: string | null;
}

interface ApiKeyListResponse {
  data: ApiKey[];
}

export function TenantApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKey, setNewKey] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { fetchKeys(); }, []);

  const fetchKeys = async () => {
    try {
      const data = await rget<ApiKeyListResponse>("/tenant/api-keys");
      setKeys(data.data || []);
    } catch {
      setMessage("Failed to load API keys");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const result = await rpost<{ key: string }>("/tenant/api-keys", { name: newKeyName });
      setNewKey(result.key);
      setMessage("API key created. Copy it now — it won't be shown again.");
      setCreateOpen(false);
      setNewKeyName("");
      fetchKeys();
    } catch {
      setMessage("Failed to create API key");
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await rdel(`/tenant/api-keys/${id}`);
      setMessage("API key revoked");
      fetchKeys();
    } catch {
      setMessage("Failed to revoke");
    }
  };

  if (loading) return <Box sx={{ p: 3 }}><Typography>Loading...</Typography></Box>;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>API Keys</Typography>
      {message && <Alert severity="info" sx={{ mb: 2 }} onClose={() => { setMessage(""); setNewKey(""); }}>{message}</Alert>}
      {newKey && <Alert severity="success" sx={{ mb: 2 }}>Key: <code>{newKey}</code></Alert>}
      <Button variant="contained" sx={{ mb: 2 }} onClick={() => setCreateOpen(true)}>Create API Key</Button>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Key Prefix</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Scopes</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Last Used</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {keys.map((k) => (
              <TableRow key={k.id}>
                <TableCell>{k.name}</TableCell>
                <TableCell><code>{k.key_prefix}...</code></TableCell>
                <TableCell><Chip label={k.status} size="small" color={k.status === "active" ? "success" : "default"} /></TableCell>
                <TableCell>{k.scopes}</TableCell>
                <TableCell>{new Date(k.created_at).toLocaleDateString()}</TableCell>
                <TableCell>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}</TableCell>
                <TableCell>
                  {k.status === "active" && <Button color="error" size="small" onClick={() => handleRevoke(k.id)}>Revoke</Button>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)}>
        <DialogTitle>Create API Key</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Name" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" disabled={!newKeyName}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
