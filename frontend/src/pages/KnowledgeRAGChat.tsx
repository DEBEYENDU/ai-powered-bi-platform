/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Slider,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import StopIcon from "@mui/icons-material/Stop";
import SettingsIcon from "@mui/icons-material/Settings";
import CloseIcon from "@mui/icons-material/Close";
import { rget, rpost } from "../api";
import { ErrorBanner } from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Collection {
  collection_id: string;
  name: string;
}

interface SourceChunk {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  document_title: string;
  text_excerpt: string;
  score: number;
  page_number: number | null;
  section: string | null;
  collection_name: string | null;
}

interface RAGResponse {
  answer: string;
  sources: SourceChunk[];
  confidence: number;
  evidence_status: string;
  query: string;
  search_time_ms: number;
  model_used: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  confidence?: number;
  evidence_status?: string;
  timestamp: string;
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
/*  Evidence Status Badge                                              */
/* ------------------------------------------------------------------ */

function EvidenceBadge({ status }: { status: string }) {
  const config: Record<string, { color: "success" | "warning" | "error"; label: string }> = {
    Supported: { color: "success", label: "Supported" },
    Insufficient: { color: "warning", label: "Insufficient Evidence" },
    Conflicting: { color: "error", label: "Conflicting Evidence" },
  };
  const c = config[status] || { color: "default" as const, label: status };
  return <Chip label={c.label} color={c.color} size="small" />;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function KnowledgeRAGChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [collectionFilter, setCollectionFilter] = useState("all");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [topK, setTopK] = useState(5);
  const [temperature, setTemperature] = useState(0.3);

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const fetchCollections = useCallback(async () => {
    try {
      const res = await rget<{ collections: Collection[] }>("/knowledge/collections");
      setCollections(res.collections || []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setError("");

    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      sources: [],
      confidence: 0,
      evidence_status: "",
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const token = localStorage.getItem("bi_token") || "";
      const res = await fetch("/api/v1/knowledge/rag/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          query: text,
          collection_id: collectionFilter === "all" ? undefined : collectionFilter,
          top_k: topK,
          temperature,
          stream: true,
        }),
        signal: abort.signal,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
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
            if (parsed.sources) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.sources = parsed.sources;
                }
                return [...updated];
              });
            }
            if (parsed.confidence !== undefined) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.confidence = parsed.confidence;
                }
                return [...updated];
              });
            }
            if (parsed.evidence_status) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  last.evidence_status = parsed.evidence_status;
                }
                return [...updated];
              });
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
          return updated;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming, collectionFilter, topK, temperature]);

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
    [handleSend]
  );

  return (
    <Box sx={{ display: "flex", height: "calc(100vh - 64px - 48px)" }}>
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
            Knowledge RAG Chat
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
                Ask questions about your documents
              </Typography>
              <Typography variant="body2">
                I'll search through your knowledge base to find relevant information and provide
                answers with citations.
              </Typography>
            </Box>
          )}
          {messages.map((msg) => (
            <Box
              key={msg.id}
              sx={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                mb: 2,
              }}
            >
              <Paper
                variant="outlined"
                sx={{
                  maxWidth: "80%",
                  p: 2,
                  borderRadius: 2,
                  bgcolor: msg.role === "user" ? "primary.dark" : "grey.900",
                  borderColor: msg.role === "user" ? "primary.dark" : "divider",
                }}
              >
                {msg.role === "user" ? (
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                    {msg.content}
                  </Typography>
                ) : (
                  <Box>
                    {msg.content && <MarkdownContent content={msg.content} />}

                    {/* Confidence & Evidence */}
                    {msg.confidence !== undefined && msg.confidence > 0 && (
                      <Box sx={{ mt: 1, display: "flex", gap: 1, alignItems: "center" }}>
                        <Typography variant="caption" color="text.secondary">
                          Confidence: {(msg.confidence * 100).toFixed(1)}%
                        </Typography>
                        {msg.evidence_status && <EvidenceBadge status={msg.evidence_status} />}
                      </Box>
                    )}

                    {/* Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <Box sx={{ mt: 2, p: 2, bgcolor: "grey.950", borderRadius: 1 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>
                          Sources
                        </Typography>
                        {msg.sources.map((source, idx) => (
                          <Box
                            key={source.chunk_id}
                            sx={{
                              mb: 1,
                              pl: 2,
                              borderLeft: "3px solid",
                              borderColor: "primary.main",
                              cursor: "pointer",
                              "&:hover": { bgcolor: "grey.900" },
                            }}
                            onClick={() => {
                              window.location.href = `/knowledge/documents/${source.document_id}`;
                            }}
                          >
                            <Typography variant="body2">
                              <strong>[{idx + 1}]</strong>{" "}
                              {source.document_title || source.document_filename}
                              {source.page_number && ` — Page ${source.page_number}`}
                              {source.section && ` — ${source.section}`}
                            </Typography>
                            <Typography
                              variant="body2"
                              color="text.secondary"
                              sx={{ fontSize: "0.85rem" }}
                            >
                              {source.text_excerpt}
                            </Typography>
                            <Chip
                              label={`${(source.score * 100).toFixed(1)}% match`}
                              size="small"
                              sx={{ mt: 0.5 }}
                            />
                          </Box>
                        ))}
                      </Box>
                    )}

                    {/* Streaming indicator */}
                    {streaming && msg.content === "" && (
                      <Box sx={{ display: "flex", gap: 0.5, mt: 1 }}>
                        <CircularProgress size={14} />
                        <Typography variant="caption" color="text.secondary">
                          Searching knowledge base...
                        </Typography>
                      </Box>
                    )}
                  </Box>
                )}
              </Paper>
            </Box>
          ))}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input area */}
        <Box sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
          <Box sx={{ display: "flex", gap: 1, alignItems: "flex-end" }}>
            <TextField
              inputRef={inputRef}
              multiline
              maxRows={6}
              placeholder="Ask a question about your documents... (Shift+Enter for new line)"
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
              <Tooltip title="Stop searching">
                <IconButton color="error" onClick={handleStop}>
                  <StopIcon />
                </IconButton>
              </Tooltip>
            ) : (
              <Tooltip title="Send query">
                <IconButton color="primary" onClick={handleSend} disabled={!input.trim()}>
                  <SendIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      </Box>

      {/* Right: Settings panel */}
      {settingsOpen && (
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
            <IconButton size="small" onClick={() => setSettingsOpen(false)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>

          <Typography variant="caption" color="text.secondary">
            Collection
          </Typography>
          <Select
            size="small"
            fullWidth
            value={collectionFilter}
            onChange={(e) => setCollectionFilter(e.target.value)}
            sx={{ mb: 2 }}
          >
            <MenuItem value="all">All Collections</MenuItem>
            {collections.map((c) => (
              <MenuItem key={c.collection_id} value={c.collection_id}>
                {c.name}
              </MenuItem>
            ))}
          </Select>

          <Typography variant="caption" color="text.secondary">
            Max Results (Top K): {topK}
          </Typography>
          <Slider
            size="small"
            value={topK}
            onChange={(_, v) => setTopK(v as number)}
            min={1}
            max={20}
            step={1}
            sx={{ mb: 2 }}
          />

          <Typography variant="caption" color="text.secondary">
            Temperature: {temperature.toFixed(2)}
          </Typography>
          <Slider
            size="small"
            value={temperature}
            onChange={(_, v) => setTemperature(v as number)}
            min={0}
            max={1}
            step={0.05}
            sx={{ mb: 2 }}
          />

          <Divider sx={{ my: 2 }} />
          <Typography variant="caption" color="text.secondary">
            Tips:
          </Typography>
          <Typography variant="body2" sx={{ fontSize: "0.8rem", mt: 0.5 }}>
            - Be specific in your questions for better results
          </Typography>
          <Typography variant="body2" sx={{ fontSize: "0.8rem" }}>
            - Use quotes for exact phrase matching
          </Typography>
          <Typography variant="body2" sx={{ fontSize: "0.8rem" }}>
            - Lower temperature for more factual answers
          </Typography>
        </Box>
      )}
    </Box>
  );
}
