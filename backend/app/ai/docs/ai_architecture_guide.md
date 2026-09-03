# AI Business Assistant Architecture Guide

## Overview

The AI Business Assistant is an enterprise-grade AI copilot for the BI platform, built on LangGraph-style orchestration with specialized agents, RAG, and tool-calling capabilities.

## Architecture

```
User Question
  -> Intent Detection (IntentDetector)
  -> Planner (create ExecutionPlan)
  -> Tool Selection & Execution (via ToolRegistry)
  -> Analytics Engine
  -> ML Engine
  -> Dashboard Engine
  -> RAG Retrieval (RAGPipeline)
  -> LLM Reasoning
  -> Hallucination Detection (HallucinationDetector)
  -> Citation Builder (CitationEngine)
  -> Response Generation
  -> Conversation Memory
  -> User
```

## Components

### Orchestrator
Coordinates the entire AI workflow: intent detection, planning, tool execution, and response generation.

### Agents
- **AnalyticsAgent**: KPI and business analytics
- **ForecastAgent**: Forecasting and predictions
- **DashboardAgent**: Dashboard analysis
- **RootCauseAgent**: Root cause analysis
- **ExecutiveSummaryAgent**: Executive summaries
- **CoordinatorAgent**: Agent coordination and routing

### RAG Pipeline
- **EmbeddingManager**: Text embeddings
- **Retriever**: Hybrid search (semantic + keyword)
- **VectorStore**: pgvector-based vector storage
- **RAGPipeline**: End-to-end retrieval-augmented generation

### Tool Registry
Central registry of all available tools with schema validation, permissions, caching, and timeout handling.

### Memory
- **ConversationMemory**: Session history, long-term memory, business context

### Prompt Management
Versioned prompt templates with approval workflows.

### Governance
- **SafetyChecker**: Input sanitization and injection prevention
- **AuditLogger**: Full audit trail
- **HallucinationDetector**: Hallucination detection and mitigation

### Monitoring
- **AIMonitor**: Performance tracking, token usage, latency metrics
