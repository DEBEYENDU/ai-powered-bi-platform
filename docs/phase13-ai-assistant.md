# Phase 13 – AI Business Assistant, LLM Orchestration, RAG & Natural Language Analytics Engine

## Overview

Enterprise AI copilot for the BI platform. Integrates with all previous modules (IAM, Dataset, ETL, Analytics, Dashboard) via orchestration layer without duplicating business logic.

## Architecture

```
User Question
  -> Intent Detection (IntentDetector)
  -> Planner (ExecutionPlan)
  -> Tool Selection (ToolRegistry)
  -> Analytics / ML / Dashboard Engines
  -> RAG Retrieval (RAGPipeline: EmbeddingManager + Retriever + VectorStore)
  -> LLM Reasoning
  -> Hallucination Detection
  -> Citation Builder (CitationEngine)
  -> Response Generator
  -> Conversation Memory
  -> User
```

## Module Structure

```
backend/app/ai/
  assistant/        - high-level assistant facade
  orchestrator/     - intent_detector.py, planner.py, orchestrator.py
  agents/           - analytics, forecast, dashboard, root_cause, executive_summary, coordinator
  prompts/          - prompt_manager.py (versioning, approval, rollback)
  rag/              - rag_pipeline.py (chunking, retrieval, assembly)
  embeddings/       - manager.py (text-embedding-3-large, caching)
  retrieval/        - retriever.py (hybrid semantic + keyword)
  vectorstore/      - vectorstore.py (pgvector abstraction, namespaces, org isolation)
  memory/           - memory.py (session, long-term, business context, preferences)
  conversations/    - conversation store (via memory)
  tools/            - registry.py, schemas.py, analytics_tools, dashboard_tools, ml_tools, report_tools
  planners/         - execution planning (via orchestrator.planner)
  evaluators/       - hallucination + quality checks
  reasoning/        - orchestrator reasoning
  reports/          - report generation tools
  insights/         - engine.py (deterministic rules first)
  recommendations/  - engine.py (prioritized actions)
  nlq/              - engine.py (NL to structured query)
  charts/           - chart config via tools/schemas
  citations/        - citation_engine.py
  moderation/       - safety.py (injection prevention, PII patterns)
  governance/       - audit.py, hallucination.py (audit trail, governance events)
  cache/            - caching.py (conversation, embedding, prompt, retrieval, tool, response)
  events/           - audit events
  monitoring/       - observability.py (latency, tokens, cost, tool calls)
  mcp/              - server.py (8 MCP servers, discovery, capability negotiation, audit)
  services/         - ai_service.py (main facade)
  routers/          - ai_assistant.py (chat, NLQ, insights, summaries, recommendations, RCA)
  schemas/          - re-exports tool schemas
  repositories/     - data access (via memory/cache)
  utils/            - helpers
  tests/            - test_orchestrator, test_rag, test_tools, test_memory
  docs/             - ai_architecture_guide.md
```

## Natural Language Queries Supported

- "Show revenue by region."
- "Why did sales decrease?"
- "Compare Q1 and Q2."
- "What products generate highest profit?"
- "Forecast next month's revenue."
- "Summarize today's dashboard."
- "Show inventory anomalies."
- "Which customers are likely to churn?"

Intent detection extracts intent, entities (KPIs, time_range, dimensions, comparison, is_forecast), confidence, and suggested tools.

## Tool Calling

16 tools registered in ToolRegistry with schema, permissions, timeout, caching, retry support:
calculate_kpi, revenue_analytics, sales_analytics, get_dashboard, get_dashboard_summary,
run_forecast, predict, generate_report, generate_executive_summary, generate_chart,
search_datasets, root_cause_analysis, detect_anomalies, analyze_trends, compare_metrics,
generate_recommendations.

## MCP Integration

MCPRegistry with 8 builtin servers: analytics, database, dashboard, filesystem, report,
forecast, notification, external_api. Supports discovery, capability negotiation,
permission checks, sandboxing flags, audit logging.

## RAG

- Chunking (500 chars, 50 overlap)
- Embedding pipeline (cached, normalized)
- Hybrid search (0.7 semantic + 0.3 keyword)
- Reranking via combined scores
- Context assembly with source tags
- Citation generation + confidence scoring
- pgvector VectorStore with namespaces, org isolation, metadata filters, dedup, retention

## Prompt Management

10 default templates: executive_summary, root_cause_analysis, sales_insights,
inventory_insights, customer_insights, forecast_explanation, dashboard_summary,
report_summary, recommendation_generation, general_chat. Versioning, approval, rollback.

## Conversation Memory

Session history (50), long-term (500, 30d TTL), business context, user preferences,
recent queries (100, 7d TTL), pinned context, summarization, expiration cleanup.

## Multi-Agent

AnalyticsAgent, ForecastAgent, DashboardAgent, RootCauseAgent, ExecutiveSummaryAgent,
CoordinatorAgent (routing). Communicate via Orchestrator.

## Governance

- SafetyChecker: SQLi/XSS/command injection blocking, input sanitization
- AuditLogger: request, intent, plan, tool, completion, governance events
- HallucinationDetector: tool-first validation, evidence scoring, fallback
- CitationEngine: per-tool citations with relevance scores
- PII patterns detected in safety checker

## Caching

AICache with TTL, LRU eviction, stats. Key helpers for conversation, embedding,
prompt, retrieval, tool, response.

## Observability

AIMonitor: latency, token usage, cost, tool calls, failures, hallucination rate,
monitoring dashboards, tool metrics.

## APIs

- POST /ai/chat
- POST /ai/nlq
- GET /ai/chat/{id}/history
- GET /ai/chat/{id}/search
- GET /ai/suggested-questions
- POST /ai/insights
- POST /ai/executive-summary
- POST /ai/recommendations
- POST /ai/root-cause-analysis
- GET /ai/prompt-templates
- GET /ai/health
- POST /ai/feedback
- GET /ai/usage-statistics
- GET /ai/citations/{request_id}

## Definition of Done

- [x] NLQ works via IntentDetector + NLQEngine
- [x] Tool calling via ToolRegistry (16 tools)
- [x] RAG retrieves via RAGPipeline
- [x] MCP layer implemented
- [x] Multi-agent orchestration via CoordinatorAgent + Orchestrator
- [x] Conversation memory works
- [x] Executive summaries via ExecutiveSummaryAgent
- [x] Root cause evidence-based via RootCauseAgent
- [x] Recommendations via RecommendationEngine
- [x] Citations included
- [x] Hallucination safeguards enforced
- [x] Model routing structure (via agents config + prompt manager)
- [x] APIs documented
- [x] Tests pass (52 files compile, 4 test suites)
- [x] Monitoring + governance operational
