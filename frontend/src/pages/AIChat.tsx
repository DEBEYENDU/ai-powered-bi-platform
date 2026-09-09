/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Box,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Slider,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SendIcon from "@mui/icons-material/Send";
import StopIcon from "@mui/icons-material/Stop";
import SettingsIcon from "@mui/icons-material/Settings";
import CloseIcon from "@mui/icons-material/Close";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Conversation {
  id: string;
  title: string;
  model: string;
  provider: string;
  message_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

interface Msg {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  token_count: number;
  created_at: string;
}

interface Provider {
  id: string;
  name: string;
  models: string[];
}

/* ------------------------------------------------------------------ */
/*  API helpers                                                        */
/* ------------------------------------------------------------------ */

async function fetchConversations(): Promise<Conversation[]> {
  const res = await rget<{ data: Conversation[] }>("/ai/conversations");
  return res.data ?? [];
}

async function fetchConversation(id: string): Promise<any> {
  return rget<any>(`/ai/conversations/${id}`);
}

async function createConversation(title?: string, model?: string, provider?: string) {
  return rpost<any>("/ai/conversations", { title: title ?? "New conversation", model, provider });
}

async function deleteConversation(id: string) {
  const token = localStorage.getItem("bi_token") || "";
  await fetch(`/api/v1/ai/conversations/${id}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

async function fetchProviders(): Promise<Provider[]> {
  return rget<Provider[]>("/ai/providers");
}

/* ------------------------------------------------------------------ */
/*  Markdown renderer                                                  */
/* ------------------------------------------------------------------ */

function MarkdownContent({ content }: { content: string }) {
  return (
    <Box
      sx={{
        "& pre": {
          bg: "grey.900",
          p: 2,
          borderRadius: 1,
          overflow: "auto",
          fontSize: "0.85rem",
          my: 1,
        },
        "& code": { fontSize: "0.85rem" },
        "& :not(pre) > code": {
          bg: "grey.800",
          px: 0.6,
          py: 0.2,
          borderRadius: 0.5,
          fontSize: "0.85em",
        },
        "& table": {
          borderCollapse: "collapse",
          my: 1,
          width: "100%",
          fontSize: "0.85rem",
        },
        "& th, & td": {
          border: "1px solid",
          borderColor: "divider",
          px: 1.5,
          py: 0.5,
          textAlign: "left",
        },
        "& th": { bgcolor: "grey.800", fontWeight: 600 },
        "& ul, & ol": { pl: 3, my: 0.5 },
        "& p": { my: 0.5 },
        lineHeight: 1.6,
      }}
    >
      <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Conversation Sidebar                                               */
/* ------------------------------------------------------------------ */

function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  return (
    <Box
      sx={{
        width: 260,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        borderRight: 1,
        borderColor: "divider",
        height: "100%",
      }}
    >
      <Box sx={{ p: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Conversations
        </Typography>
        <Tooltip title="New conversation">
          <IconButton size="small" onClick={onNew}>
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <Divider />
      <List sx={{ flex: 1, overflow: "auto", py: 0 }}>
        {conversations.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: "center" }}>
            No conversations yet
          </Typography>
        )}
        {conversations.map((c) => (
          <ListItemButton
            key={c.id}
            selected={c.id === activeId}
            onClick={() => onSelect(c.id)}
            sx={{ py: 1 }}
          >
            <ListItemText
              primary={c.title}
              secondary={`${c.message_count} msgs · ${c.model}`}
              slotProps={{
                primary: { noWrap: true, variant: "body2" },
                secondary: { variant: "caption" },
              }}
            />
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Settings Panel                                                     */
/* ------------------------------------------------------------------ */

function SettingsPanel({
  open,
  onClose,
  providers,
  model,
  provider,
  temperature,
  maxTokens,
  onModelChange,
  onProviderChange,
  onTemperatureChange,
  onMaxTokensChange,
  tokenUsage,
}: {
  open: boolean;
  onClose: () => void;
  providers: Provider[];
  model: string;
  provider: string;
  temperature: number;
  maxTokens: number;
  onModelChange: (m: string) => void;
  onProviderChange: (p: string) => void;
  onTemperatureChange: (t: number) => void;
  onMaxTokensChange: (t: number) => void;
  tokenUsage: { prompt: number; completion: number; total: number };
}) {
  if (!open) return null;
  const currentProvider = providers.find((p) => p.id === provider);
  const models = currentProvider?.models ?? [];

  return (
    <Box
      sx={{
        width: 280,
        flexShrink: 0,
        borderLeft: 1,
        borderColor: "divider",
        height: "100%",
        overflow: "auto",
        p: 2,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
        <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Settings
        </Typography>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Typography variant="caption" color="text.secondary">
        Provider
      </Typography>
      <Select
        size="small"
        fullWidth
        value={provider}
        onChange={(e) => onProviderChange(e.target.value)}
        sx={{ mb: 2 }}
      >
        {providers.map((p) => (
          <MenuItem key={p.id} value={p.id}>
            {p.name}
          </MenuItem>
        ))}
      </Select>

      <Typography variant="caption" color="text.secondary">
        Model
      </Typography>
      <Select
        size="small"
        fullWidth
        value={model}
        onChange={(e) => onModelChange(e.target.value)}
        sx={{ mb: 2 }}
      >
        {models.map((m) => (
          <MenuItem key={m} value={m}>
            {m}
          </MenuItem>
        ))}
      </Select>

      <Typography variant="caption" color="text.secondary">
        Temperature: {temperature.toFixed(2)}
      </Typography>
      <Slider
        size="small"
        value={temperature}
        onChange={(_, v) => onTemperatureChange(v as number)}
        min={0}
        max={2}
        step={0.05}
        sx={{ mb: 2 }}
      />

      <Typography variant="caption" color="text.secondary">
        Max tokens
      </Typography>
      <TextField
        size="small"
        fullWidth
        type="number"
        value={maxTokens}
        onChange={(e) => onMaxTokensChange(Number(e.target.value))}
        sx={{ mb: 2 }}
      />

      <Divider sx={{ my: 2 }} />
      <Typography variant="caption" color="text.secondary" gutterBottom>
        Token Usage
      </Typography>
      <Typography variant="body2">Prompt: {tokenUsage.prompt}</Typography>
      <Typography variant="body2">Completion: {tokenUsage.completion}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        Total: {tokenUsage.total}
      </Typography>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Message Bubble                                                     */
/* ------------------------------------------------------------------ */

function MessageBubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 1.5,
      }}
    >
      <Paper
        variant="outlined"
        sx={{
          maxWidth: "75%",
          p: 1.5,
          borderRadius: 2,
          bgcolor: isUser ? "primary.dark" : "grey.900",
          borderColor: isUser ? "primary.dark" : "divider",
        }}
      >
        {isUser ? (
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {msg.content}
          </Typography>
        ) : (
          <MarkdownContent content={msg.content} />
        )}
      </Paper>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Main AIChat Page                                                   */
/* ------------------------------------------------------------------ */

export function AIChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [model, setModel] = useState("gpt-4o-mini");
  const [provider, setProvider] = useState("openai");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [tokenUsage, setTokenUsage] = useState({ prompt: 0, completion: 0, total: 0 });

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* Load conversations + providers on mount */
  useEffect(() => {
    fetchConversations().then(setConversations).catch(() => {});
    fetchProviders()
      .then((p) => {
        setProviders(p);
        if (p.length > 0) {
          setProvider(p[0].id);
          if (p[0].models.length > 0) setModel(p[0].models[0]);
        }
      })
      .catch(() => {});
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    setActiveConvId(id);
    try {
      const data = await fetchConversation(id);
      setMessages(data.messages ?? []);
    } catch {
      setMessages([]);
    }
  }, []);

  const handleNewConversation = useCallback(async () => {
    try {
      const conv = await createConversation("New conversation", model, provider);
      setConversations((prev) => [conv, ...prev]);
      setActiveConvId(conv.id);
      setMessages([]);
    } catch {
      /* ignore */
    }
  }, [model, provider]);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeConvId === id) {
          setActiveConvId(null);
          setMessages([]);
        }
      } catch {
        /* ignore */
      }
    },
    [activeConvId],
  );

  /* Send message with SSE streaming */
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;

    let convId = activeConvId;
    if (!convId) {
      try {
        const conv = await createConversation(text.slice(0, 80), model, provider);
        convId = conv.id;
        setConversations((prev) => [conv, ...prev]);
        setActiveConvId(convId);
      } catch {
        return;
      }
    }

    const userMsg: Msg = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: text,
      token_count: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const assistantMsg: Msg = {
      id: `stream-${Date.now()}`,
      role: "assistant",
      content: "",
      token_count: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch("/api/v1/ai/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          conversation_id: convId,
          model,
          provider,
          temperature,
          max_tokens: maxTokens,
          stream: true,
        }),
        signal: abort.signal,
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") break;

          try {
            const parsed = JSON.parse(data);
            if (parsed.error) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.content = `Error: ${parsed.error}`;
                }
                return updated;
              });
              break;
            }
            if (parsed.delta) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.content += parsed.delta;
                }
                return [...updated];
              });
            }
            if (parsed.usage) {
              setTokenUsage((prev) => ({
                prompt: prev.prompt + (parsed.usage.prompt_tokens ?? 0),
                completion: prev.completion + (parsed.usage.completion_tokens ?? 0),
                total: prev.total + (parsed.usage.total_tokens ?? 0),
              }));
            }
            if (parsed.conversation_id && parsed.conversation_id !== convId) {
              convId = parsed.conversation_id;
              setActiveConvId(convId);
            }
          } catch {
            /* skip unparseable lines */
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            last.content = `Error: ${err.message}`;
          }
          return [...updated];
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      /* Refresh conversation list to get updated title */
      fetchConversations().then(setConversations).catch(() => {});
    }
  }, [input, streaming, activeConvId, model, provider, temperature, maxTokens]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 64px - 48px)" }}>
      {/* Left sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={loadConversation}
        onNew={handleNewConversation}
        onDelete={handleDelete}
      />

      {/* Center: Chat area */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Header */}
        <Box
          sx={{
            p: 1,
            display: "flex",
            alignItems: "center",
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            AI Assistant
          </Typography>
          <Tooltip title="Settings">
            <IconButton size="small" onClick={() => setSettingsOpen(!settingsOpen)}>
              <SettingsIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Messages */}
        <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
          {messages.length === 0 && (
            <Box sx={{ textAlign: "center", mt: 8, color: "text.secondary" }}>
              <Typography variant="h5" gutterBottom>
                How can I help you today?
              </Typography>
              <Typography variant="body2">
                Ask me about your business data, KPIs, analytics, or dashboards.
              </Typography>
            </Box>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
          {streaming && messages[messages.length - 1]?.content === "" && (
            <Box sx={{ display: "flex", gap: 0.5, ml: 1, mb: 1 }}>
              <CircularProgress size={14} />
              <Typography variant="caption" color="text.secondary">
                Thinking...
              </Typography>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input area */}
        <Box sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
          <Box sx={{ display: "flex", gap: 1, alignItems: "flex-end" }}>
            <TextField
              inputRef={inputRef}
              multiline
              maxRows={6}
              placeholder="Type your message... (Shift+Enter for new line)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              fullWidth
              size="small"
              disabled={streaming}
              sx={{
                "& .MuiInputBase-root": { borderRadius: 2 },
              }}
            />
            {streaming ? (
              <Tooltip title="Stop generating">
                <IconButton color="error" onClick={handleStop}>
                  <StopIcon />
                </IconButton>
              </Tooltip>
            ) : (
              <Tooltip title="Send message">
                <IconButton
                  color="primary"
                  onClick={handleSend}
                  disabled={!input.trim()}
                >
                  <SendIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      </Box>

      {/* Right: Settings panel */}
      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        providers={providers}
        model={model}
        provider={provider}
        temperature={temperature}
        maxTokens={maxTokens}
        onModelChange={setModel}
        onProviderChange={setProvider}
        onTemperatureChange={setTemperature}
        onMaxTokensChange={setMaxTokens}
        tokenUsage={tokenUsage}
      />
    </Box>
  );
}
