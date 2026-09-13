/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import PendingIcon from "@mui/icons-material/Pending";
import StopIcon from "@mui/icons-material/Stop";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { rget, rpost } from "../api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface StepInfo {
  step_id: string;
  tool_name: string;
  purpose: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  duration_ms?: number;
}

interface ResultPart {
  type: "text" | "table" | "chart" | "findings" | "citations" | "warning" | "insights" | "forecast" | "report";
  content?: string;
  items?: string[];
  columns?: string[];
  rows?: Record<string, any>[];
  config?: any;
  source?: string;
}

interface CopilotMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  steps?: StepInfo[];
  result_parts?: ResultPart[];
  confidence?: number;
  timestamp: string;
}

interface CopilotTaskResponse {
  task_id: string;
  session_id: string;
  status: string;
  request: string;
  intent: string | null;
  intent_confidence: number | null;
  steps: StepInfo[];
  answer: string | null;
  answer_parts: ResultPart[];
  tools_used: string[];
  total_steps: number;
  completed_steps: number;
  error: string | null;
}

interface Session {
  id: string;
  title: string | null;
  message_count: number;
  created_at: string;
}

interface CopilotTool {
  name: string;
  description: string;
  risk_level: string;
}

/* ------------------------------------------------------------------ */
/*  API helpers                                                        */
/* ------------------------------------------------------------------ */

async function fetchSessions(): Promise<Session[]> {
  const res = await rget<{ data: Session[] }>("/copilot/sessions");
  return res.data ?? [];
}

async function createSession(title?: string): Promise<Session> {
  return rpost<Session>("/copilot/sessions", { title: title ?? "New session" });
}

async function fetchTools(): Promise<CopilotTool[]> {
  const res = await rget<{ data: CopilotTool[] }>("/copilot/tools");
  return res.data ?? [];
}

/* ------------------------------------------------------------------ */
/*  Markdown renderer                                                  */
/* ------------------------------------------------------------------ */

function MarkdownContent({ content }: { content: string }) {
  return (
    <Box
      sx={{
        "& pre": {
          bgcolor: "grey.900",
          p: 2,
          borderRadius: 1,
          overflow: "auto",
          fontSize: "0.85rem",
          my: 1,
        },
        "& code": { fontSize: "0.85rem" },
        "& :not(pre) > code": {
          bgcolor: "grey.800",
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
/*  Execution Steps Display                                            */
/* ------------------------------------------------------------------ */

function ExecutionSteps({ steps }: { steps: StepInfo[] }) {
  if (!steps || steps.length === 0) return null;
  return (
    <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Execution Plan
      </Typography>
      {steps.map((step) => (
        <Box key={step.step_id} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
          {step.status === "completed" ? (
            <CheckCircleIcon fontSize="small" color="success" />
          ) : step.status === "running" ? (
            <CircularProgress size={16} />
          ) : step.status === "failed" ? (
            <ErrorIcon fontSize="small" color="error" />
          ) : (
            <PendingIcon fontSize="small" color="disabled" />
          )}
          <Typography variant="body2" sx={{ flex: 1 }}>
            {step.purpose || step.tool_name}
          </Typography>
          <Chip label={step.tool_name} size="small" variant="outlined" />
          {step.duration_ms != null && (
            <Typography variant="caption" color="text.secondary">
              {step.duration_ms.toFixed(0)}ms
            </Typography>
          )}
        </Box>
      ))}
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Result Parts Rendering                                             */
/* ------------------------------------------------------------------ */

function ResultPartView({ part }: { part: ResultPart }) {
  switch (part.type) {
    case "text":
      return part.content ? (
        <Box sx={{ mb: 2 }}>
          <MarkdownContent content={part.content} />
        </Box>
      ) : null;

    case "table":
      return part.columns && part.rows ? (
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {part.columns.map((col) => (
                  <TableCell key={col} sx={{ fontWeight: 600 }}>
                    {col}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {part.rows.map((row, i) => (
                <TableRow key={i}>
                  {part.columns!.map((col) => (
                    <TableCell key={col}>{row[col] ?? ""}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null;

    case "findings":
      return part.items && part.items.length > 0 ? (
        <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Key Findings
          </Typography>
          <List dense sx={{ py: 0 }}>
            {part.items.map((item, i) => (
              <ListItemButton key={i} dense sx={{ py: 0 }}>
                <ListItemText primary={item} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      ) : null;

    case "citations":
      return part.items && part.items.length > 0 ? (
        <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Sources
          </Typography>
          {part.items.map((src, i) => (
            <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
              <Typography variant="body2" sx={{ flex: 1 }}>
                {src}
              </Typography>
              {part.source && (
                <Chip label={part.source} size="small" variant="outlined" />
              )}
            </Box>
          ))}
        </Box>
      ) : null;

    case "warning":
      return part.content ? (
        <Alert severity="warning" sx={{ mb: 2 }} icon={<WarningAmberIcon />}>
          {part.content}
        </Alert>
      ) : null;

    case "chart":
      return (
        <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Chart
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {part.content ?? "Chart visualization"}
          </Typography>
          {part.config && (
            <Box
              component="pre"
              sx={{
                mt: 1,
                p: 1,
                bgcolor: "grey.800",
                borderRadius: 1,
                overflow: "auto",
                fontSize: "0.8rem",
                maxHeight: 200,
              }}
            >
              {JSON.stringify(part.config, null, 2)}
            </Box>
          )}
        </Box>
      );

    case "insights":
      return part.items && part.items.length > 0 ? (
        <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Insights
          </Typography>
          {part.items.map((insight, i) => (
            <Box key={i} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
              <Typography variant="body2" sx={{ flex: 1 }}>
                {insight}
              </Typography>
              {part.config?.confidence != null && (
                <Chip
                  label={`${(part.config.confidence * 100).toFixed(0)}%`}
                  size="small"
                  color="info"
                  variant="outlined"
                />
              )}
            </Box>
          ))}
        </Box>
      ) : null;

    case "forecast":
      return (
        <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Forecast
          </Typography>
          {part.content && (
            <MarkdownContent content={part.content} />
          )}
          {part.items && part.items.length > 0 && (
            <List dense sx={{ py: 0 }}>
              {part.items.map((item, i) => (
                <ListItemButton key={i} dense sx={{ py: 0 }}>
                  <ListItemText primary={item} />
                </ListItemButton>
              ))}
            </List>
          )}
        </Box>
      );

    case "report":
      return (
        <Box sx={{ mb: 2, p: 2, bgcolor: "grey.900", borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Report
          </Typography>
          {part.content && <MarkdownContent content={part.content} />}
          {part.config?.link && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" color="primary" component="a" href={part.config.link} target="_blank" rel="noopener">
                View Full Report
              </Typography>
            </Box>
          )}
        </Box>
      );

    default:
      return null;
  }
}

/* ------------------------------------------------------------------ */
/*  Message Bubble                                                     */
/* ------------------------------------------------------------------ */

function MessageBubble({ msg }: { msg: CopilotMessage }) {
  const isUser = msg.role === "user";
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 2,
      }}
    >
      <Paper
        variant="outlined"
        sx={{
          maxWidth: "80%",
          p: 2,
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
          <Box>
            {msg.steps && msg.steps.length > 0 && <ExecutionSteps steps={msg.steps} />}
            {msg.content && <MarkdownContent content={msg.content} />}
            {msg.result_parts &&
              msg.result_parts.map((part, i) => <ResultPartView key={i} part={part} />)}
            {msg.confidence != null && (
              <Box sx={{ mt: 1 }}>
                <Chip
                  label={`Confidence: ${(msg.confidence * 100).toFixed(0)}%`}
                  size="small"
                  variant="outlined"
                  color={msg.confidence > 0.8 ? "success" : "default"}
                />
              </Box>
            )}
          </Box>
        )}
      </Paper>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Conversation Sidebar                                               */
/* ------------------------------------------------------------------ */

function ConversationSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
}: {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
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
      <Box
        sx={{
          p: 1.5,
          borderBottom: 1,
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
        }}
      >
        <Typography variant="subtitle2" sx={{ flex: 1, fontWeight: 600 }}>
          Copilot Sessions
        </Typography>
        <IconButton size="small" onClick={onNew}>
          <AddIcon fontSize="small" />
        </IconButton>
      </Box>
      <List sx={{ flex: 1, overflow: "auto", py: 0 }}>
        {sessions.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: "center" }}>
            No sessions yet
          </Typography>
        )}
        {sessions.map((s) => (
          <ListItemButton
            key={s.id}
            selected={s.id === activeId}
            onClick={() => onSelect(s.id)}
            sx={{ py: 1 }}
          >
            <ListItemText
              primary={s.title || "New Session"}
              secondary={`${s.message_count} messages`}
              slotProps={{
                primary: { noWrap: true, variant: "body2" },
                secondary: { variant: "caption" },
              }}
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Copilot Page                                                  */
/* ------------------------------------------------------------------ */

export function Copilot() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [currentSteps, setCurrentSteps] = useState<StepInfo[]>([]);
  const [lastIntent, setLastIntent] = useState<string | null>(null);
  const [lastConfidence, setLastConfidence] = useState<number | null>(null);
  const [tools, setTools] = useState<CopilotTool[]>([]);
  const [error, setError] = useState("");

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* Load sessions + tools on mount */
  useEffect(() => {
    fetchSessions().then(setSessions).catch(() => {});
    fetchTools().then(setTools).catch(() => {});
  }, []);

  const loadSession = useCallback(async (id: string) => {
    setActiveSessionId(id);
    setMessages([]);
    setCurrentSteps([]);
    setLastIntent(null);
    setLastConfidence(null);
  }, []);

  const handleNewSession = useCallback(async () => {
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setCurrentSteps([]);
      setLastIntent(null);
      setLastConfidence(null);
    } catch {
      /* ignore */
    }
  }, []);

  /* Send query with SSE streaming */
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createSession(text.slice(0, 80));
        sessionId = session.id;
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(sessionId);
      } catch {
        return;
      }
    }

    const userMsg: CopilotMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setError("");
    setCurrentSteps([]);

    const assistantMsg: CopilotMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      steps: [],
      result_parts: [],
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch("/api/v1/copilot/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          query: text,
          session_id: sessionId,
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
              setError(parsed.error);
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

            if (parsed.steps) {
              setCurrentSteps(parsed.steps);
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.steps = parsed.steps;
                }
                return [...updated];
              });
            }

            if (parsed.result_parts) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.result_parts = parsed.result_parts;
                }
                return [...updated];
              });
            }

            if (parsed.answer) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.content = parsed.answer;
                }
                return [...updated];
              });
            }

            if (parsed.intent) {
              setLastIntent(parsed.intent);
              setLastConfidence(parsed.intent_confidence);
            }

            if (parsed.confidence != null) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.confidence = parsed.confidence;
                }
                return [...updated];
              });
            }

            if (parsed.session_id && parsed.session_id !== sessionId) {
              sessionId = parsed.session_id;
              setActiveSessionId(sessionId);
            }
          } catch {
            /* skip unparseable lines */
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setError(err.message);
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
      setCurrentSteps([]);
      fetchSessions().then(setSessions).catch(() => {});
    }
  }, [input, streaming, activeSessionId]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
    setCurrentSteps([]);
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
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={loadSession}
        onNew={handleNewSession}
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
            BI Copilot
          </Typography>
          <Chip
            label={`${tools.length} tools available`}
            size="small"
            variant="outlined"
            sx={{ mr: 1 }}
          />
        </Box>

        {/* Messages */}
        <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
              {error}
            </Alert>
          )}

          {messages.length === 0 && (
            <Box sx={{ textAlign: "center", mt: 8, color: "text.secondary" }}>
              <Typography variant="h5" gutterBottom>
                Ask me anything about your business data
              </Typography>
              <Typography variant="body2">
                I can help you analyze data, generate reports, and provide insights.
              </Typography>
              <Box sx={{ mt: 3, display: "flex", justifyContent: "center", gap: 1, flexWrap: "wrap" }}>
                {["Show me last quarter's sales", "What are our top-performing products?", "Generate a revenue forecast"].map(
                  (q) => (
                    <Chip
                      key={q}
                      label={q}
                      onClick={() => setInput(q)}
                      variant="outlined"
                      sx={{ cursor: "pointer" }}
                    />
                  ),
                )}
              </Box>
            </Box>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}

          {streaming && currentSteps.length === 0 && messages[messages.length - 1]?.content === "" && (
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
              placeholder="Ask about your business data... (e.g., 'Show me last quarter's sales')"
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
              <Tooltip title="Stop">
                <IconButton color="error" onClick={handleStop}>
                  <StopIcon />
                </IconButton>
              </Tooltip>
            ) : (
              <Tooltip title="Send">
                <IconButton color="primary" onClick={handleSend} disabled={!input.trim()}>
                  <AutoFixHighIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
          {lastIntent && (
            <Box sx={{ mt: 0.5, display: "flex", gap: 1 }}>
              <Chip label={`Intent: ${lastIntent}`} size="small" color="info" variant="outlined" />
              {lastConfidence != null && (
                <Chip
                  label={`${(lastConfidence * 100).toFixed(0)}% confident`}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}
