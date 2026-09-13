/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { rget } from "../api";
import { ErrorBanner, EmptyState } from "../components";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Collection {
  collection_id: string;
  name: string;
}

interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  document_title: string;
  text_excerpt: string;
  score: number;
  page_number: number | null;
  section: string | null;
  collection_name: string | null;
  collection_id: string;
}

interface SearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  search_time_ms: number;
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */

export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const [collectionFilter, setCollectionFilter] = useState("all");
  const [searchType, setSearchType] = useState("semantic");
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

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

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    setHasSearched(true);

    try {
      const params = new URLSearchParams();
      params.set("q", query.trim());
      params.set("top_k", String(topK));
      params.set("search_type", searchType);
      if (collectionFilter !== "all") params.set("collection_id", collectionFilter);

      const res = await rget<SearchResponse>(`/knowledge/search?${params.toString()}`);
      setResults(res.results || []);
      setSearchTime(res.search_time_ms || null);
    } catch (e: any) {
      setError(e.message || "Search failed");
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, [query, topK, searchType, collectionFilter]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const highlightText = (text: string, maxLen: number = 300) => {
    if (text.length <= maxLen) return text;
    return text.substring(0, maxLen) + "...";
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Knowledge Search
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Search through your knowledge base using semantic or keyword search
      </Typography>

      <ErrorBanner error={error} />

      {/* Search Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", gap: 2, mb: 2, alignItems: "flex-end" }}>
          <TextField
            fullWidth
            size="small"
            label="Search Query"
            placeholder="Enter your search query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <Button
            variant="contained"
            startIcon={searching ? <CircularProgress size={18} /> : <SearchIcon />}
            onClick={handleSearch}
            disabled={!query.trim() || searching}
            sx={{ minWidth: 140, height: 40 }}
          >
            {searching ? "Searching..." : "Search"}
          </Button>
        </Box>

        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <TextField
            select
            size="small"
            label="Collection"
            value={collectionFilter}
            onChange={(e) => setCollectionFilter(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 180 }}
          >
            <MenuItem value="all">All Collections</MenuItem>
            {collections.map((c) => (
              <MenuItem key={c.collection_id} value={c.collection_id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            size="small"
            label="Search Type"
            value={searchType}
            onChange={(e) => setSearchType(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="semantic">Semantic</MenuItem>
            <MenuItem value="keyword">Keyword</MenuItem>
            <MenuItem value="hybrid">Hybrid</MenuItem>
          </TextField>

          <TextField
            select
            size="small"
            label="Max Results"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 120 }}
          >
            {[5, 10, 20, 50].map((n) => (
              <MenuItem key={n} value={n}>
                {n}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      </Paper>

      {/* Search Results */}
      {searching ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      ) : hasSearched && results.length === 0 ? (
        <EmptyState message="No results found. Try a different query or adjust your filters." />
      ) : (
        <>
          {searchTime !== null && results.length > 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Found {results.length} result{results.length !== 1 ? "s" : ""} in {searchTime}ms
            </Typography>
          )}

          {results.map((result, idx) => (
            <Paper
              key={result.chunk_id}
              sx={{
                p: 2,
                mb: 1,
                cursor: "pointer",
                transition: "all 0.2s",
                "&:hover": { borderColor: "primary.main", borderWidth: 1, borderStyle: "solid" },
              }}
              onClick={() => {
                window.location.href = `/knowledge/documents/${result.document_id}`;
              }}
            >
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {result.document_title || result.document_filename}
                </Typography>
                <Chip
                  label={`${(result.score * 100).toFixed(1)}%`}
                  size="small"
                  color="primary"
                />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {highlightText(result.text_excerpt)}
              </Typography>
              <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                {result.page_number && (
                  <Chip label={`Page ${result.page_number}`} size="small" variant="outlined" />
                )}
                {result.section && (
                  <Chip label={result.section} size="small" variant="outlined" />
                )}
                {result.collection_name && (
                  <Chip label={result.collection_name} size="small" variant="outlined" />
                )}
                <Chip
                  label={result.document_filename}
                  size="small"
                  variant="outlined"
                  color="secondary"
                />
              </Box>
            </Paper>
          ))}
        </>
      )}

      {/* Initial State */}
      {!hasSearched && !searching && (
        <Box sx={{ textAlign: "center", mt: 8, color: "text.secondary" }}>
          <SearchIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
          <Typography variant="h6">Search your knowledge base</Typography>
          <Typography variant="body2">
            Enter a query above to find relevant documents, sections, and excerpts.
          </Typography>
        </Box>
      )}
    </Box>
  );
}
