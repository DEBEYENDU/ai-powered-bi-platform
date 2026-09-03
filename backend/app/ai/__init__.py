"""AI Business Assistant Module.

Phase 13: AI Business Assistant, LLM Orchestration, RAG & Natural Language Analytics Engine.

Provides:
- Natural Language Query Engine
- Multi-Agent Orchestration
- RAG Pipeline
- Tool Registry
- Prompt Management
- Conversation Memory
- MCP Integration Layer
- Governance & Hallucination Detection
"""

from app.ai.orchestrator.orchestrator import Orchestrator
from app.ai.orchestrator.intent_detector import IntentDetector, IntentDetection, IntentType
from app.ai.orchestrator.planner import Planner, ExecutionPlan, PlanStep
from app.ai.tools.registry import ToolRegistry, ToolDefinition
from app.ai.tools.schemas import (
    NLQQuery, KPICalculateRequest, KPICalculateResponse,
    RevenueAnalyticsRequest, RevenueAnalyticsResponse,
    SalesAnalyticsRequest, SalesAnalyticsResponse,
    ForecastRequest, ForecastResponse,
    ChatRequest, ChatResponse,
)
from app.ai.rag.rag_pipeline import RAGPipeline, RAGResult, RAGConfig
from app.ai.memory.memory import ConversationMemory, MemoryEntry, MemoryType
from app.ai.prompts.prompt_manager import PromptManager, PromptTemplate, PromptVersion
from app.ai.embeddings.manager import EmbeddingManager, EmbeddingConfig
from app.ai.retrieval.retriever import Retriever, RetrievalResult
from app.ai.vectorstore.vectorstore import VectorStore, VectorRecord
from app.ai.cache.caching import AICache, CacheEntry
from app.ai.moderation.safety import SafetyChecker, SafetyCheckResult
from app.ai.governance.audit import AuditLogger, AuditEntry
from app.ai.governance.hallucination import HallucinationDetector, HallucinationRisk
from app.ai.citations.citation_engine import CitationEngine, Citation, CitationResponse
from app.ai.agents.analytics_agent import AnalyticsAgent
from app.ai.agents.forecast_agent import ForecastAgent
from app.ai.agents.dashboard_agent import DashboardAgent
from app.ai.agents.root_cause_agent import RootCauseAgent
from app.ai.agents.executive_summary_agent import ExecutiveSummaryAgent
from app.ai.agents.coordinator_agent import CoordinatorAgent
from app.ai.monitoring.observability import AIMonitor, TokenUsage, LatencyMetric, AIMetric
from app.ai.services.ai_service import AIService
from app.ai.mcp.server import MCPRegistry, MCPServerInfo, MCPTool
from app.ai.nlq.engine import NLQEngine
from app.ai.insights.engine import InsightsEngine
from app.ai.recommendations.engine import RecommendationEngine

__all__ = [
    "Orchestrator", "IntentDetector", "IntentDetection", "IntentType", "Planner",
    "ExecutionPlan", "PlanStep",
    "ToolRegistry", "ToolDefinition",
    "NLQQuery", "KPICalculateRequest", "KPICalculateResponse",
    "RevenueAnalyticsRequest", "RevenueAnalyticsResponse",
    "SalesAnalyticsRequest", "SalesAnalyticsResponse",
    "ForecastRequest", "ForecastResponse", "ChatRequest", "ChatResponse",
    "RAGPipeline", "RAGResult", "RAGConfig",
    "ConversationMemory", "MemoryEntry", "MemoryType",
    "PromptManager", "PromptTemplate", "PromptVersion",
    "EmbeddingManager", "EmbeddingConfig",
    "Retriever", "RetrievalResult",
    "VectorStore", "VectorRecord",
    "AICache", "CacheEntry",
    "SafetyChecker", "SafetyCheckResult",
    "AuditLogger", "AuditEntry",
    "HallucinationDetector", "HallucinationRisk",
    "CitationEngine", "Citation", "CitationResponse",
    "AnalyticsAgent", "ForecastAgent", "DashboardAgent",
    "RootCauseAgent", "ExecutiveSummaryAgent", "CoordinatorAgent",
    "AIMonitor", "TokenUsage", "LatencyMetric", "AIMetric",
    "AIService",
    "MCPRegistry", "MCPServerInfo", "MCPTool",
    "NLQEngine", "InsightsEngine", "RecommendationEngine",
]
