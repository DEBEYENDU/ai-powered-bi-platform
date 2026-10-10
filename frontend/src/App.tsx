import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { Box, CircularProgress } from "@mui/material";
import { ensureValidSession, getAuthStatus, onAuthChange } from "./api";
import { Layout } from "./components";
import { AgentDashboard } from "./pages/AgentDashboard";
import { AgentLogs } from "./pages/AgentLogs";
import { AgentStatus } from "./pages/AgentStatus";
import { WorkflowApprovals } from "./pages/WorkflowApprovals";
import { WorkflowBuilder } from "./pages/WorkflowBuilder";
import { WorkflowDetails } from "./pages/WorkflowDetails";
import { WorkflowExecutionDetails } from "./pages/WorkflowExecutionDetails";
import { WorkflowHistory } from "./pages/WorkflowHistory";
import { WorkflowTemplates } from "./pages/WorkflowTemplates";
import { Workflows } from "./pages/Workflows";
import { AIDashboardGenerator } from "./pages/AIDashboardGenerator";
import { AIAdmin } from "./pages/AIAdmin";
import { AIChat } from "./pages/AIChat";
import { Alerts } from "./pages/Alerts";
import { AskYourData } from "./pages/AskYourData";
import { Audit } from "./pages/Audit";
import { BusinessInsights } from "./pages/BusinessInsights";
import { Dashboards } from "./pages/Dashboards";
import { DataCleaning } from "./pages/DataCleaning";
import { DataPipelines } from "./pages/DataPipelines";
import { DataQuality } from "./pages/DataQuality";
import { DataSources } from "./pages/DataSources";
import { DataTransform } from "./pages/DataTransform";
import { ExecutionGraph } from "./pages/ExecutionGraph";
import { Flags } from "./pages/Flags";
import { Forecasting } from "./pages/Forecasting";
import { Health } from "./pages/Health";
import { Jobs } from "./pages/Jobs";
import { KnowledgeBase } from "./pages/KnowledgeBase";
import { KnowledgeCollections } from "./pages/KnowledgeCollections";
import { KnowledgeDocumentDetail } from "./pages/KnowledgeDocumentDetail";
import { KnowledgeDocuments } from "./pages/KnowledgeDocuments";
import { KnowledgeRAGChat } from "./pages/KnowledgeRAGChat";
import { KnowledgeSearch } from "./pages/KnowledgeSearch";
import { KnowledgeUpload } from "./pages/KnowledgeUpload";
import { Login } from "./pages/Login";
import { MemoryViewer } from "./pages/MemoryViewer";
import { Metrics } from "./pages/Metrics";
import { ModelManagement } from "./pages/ModelManagement";
import { ModelPerformance } from "./pages/ModelPerformance";
import { Organizations } from "./pages/Organizations";
import { Overview } from "./pages/Overview";
import { Reports } from "./pages/Reports";
import { ReportsLibrary } from "./pages/ReportsLibrary";
import { Roles } from "./pages/Roles";
import { ScenarioAnalysis } from "./pages/ScenarioAnalysis";
import { MLOps } from "./pages/MLOps";
import { MLOpsModels } from "./pages/MLOpsModels";
import { MLOpsModelDetail } from "./pages/MLOpsModelDetail";
import { MLOpsExperiments } from "./pages/MLOpsExperiments";
import { MLOpsTraining } from "./pages/MLOpsTraining";
import { MLOpsDeployments } from "./pages/MLOpsDeployments";
import { MLOpsMonitoring } from "./pages/MLOpsMonitoring";
import { MLOpsDrift } from "./pages/MLOpsDrift";
import { Governance } from "./pages/Governance";
import { GovernancePolicies } from "./pages/GovernancePolicies";
import { GovernanceSecurity } from "./pages/GovernanceSecurity";
import { GovernanceClassifications } from "./pages/GovernanceClassifications";
import { Settings } from "./pages/Settings";
import { TaskHistory } from "./pages/TaskHistory";
import { TenantApiKeys } from "./pages/TenantApiKeys";
import { TenantOrganization } from "./pages/TenantOrganization";
import { TenantUsage } from "./pages/TenantUsage";
import { Users } from "./pages/Users";

/** Shared auth status: unknown -> (refresh) -> authenticated | unauthenticated. */
function useAuthStatus() {
  const [status, setStatus] = useState(getAuthStatus());
  useEffect(() => onAuthChange(setStatus), []);
  useEffect(() => {
    // Access token present but expired: resolve it with the refresh token
    // before any protected page renders, instead of bouncing to /login.
    if (status === "unknown") void ensureValidSession();
  }, [status]);
  return status;
}

function FullPageLoading() {
  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <CircularProgress />
    </Box>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuthStatus();
  if (status === "unknown") return <FullPageLoading />;
  if (status === "unauthenticated") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Layout><Overview /></Layout></RequireAuth>} />
        <Route path="/users" element={<RequireAuth><Layout><Users /></Layout></RequireAuth>} />
        <Route path="/orgs" element={<RequireAuth><Layout><Organizations /></Layout></RequireAuth>} />
        <Route path="/roles" element={<RequireAuth><Layout><Roles /></Layout></RequireAuth>} />
        <Route path="/dashboards" element={<RequireAuth><Layout><Dashboards /></Layout></RequireAuth>} />
        <Route path="/reports" element={<RequireAuth><Layout><Reports /></Layout></RequireAuth>} />
        <Route path="/ai" element={<RequireAuth><Layout><AIAdmin /></Layout></RequireAuth>} />
        <Route path="/ai/chat" element={<RequireAuth><Layout><AIChat /></Layout></RequireAuth>} />
        <Route path="/ai/ask" element={<RequireAuth><Layout><AskYourData /></Layout></RequireAuth>} />
        <Route path="/ai/dashboard-gen" element={<RequireAuth><Layout><AIDashboardGenerator /></Layout></RequireAuth>} />
        <Route path="/ai/insights" element={<RequireAuth><Layout><BusinessInsights /></Layout></RequireAuth>} />
        <Route path="/ai/reports" element={<RequireAuth><Layout><ReportsLibrary /></Layout></RequireAuth>} />
        <Route path="/de/sources" element={<RequireAuth><Layout><DataSources /></Layout></RequireAuth>} />
        <Route path="/de/quality" element={<RequireAuth><Layout><DataQuality /></Layout></RequireAuth>} />
        <Route path="/de/cleaning" element={<RequireAuth><Layout><DataCleaning /></Layout></RequireAuth>} />
        <Route path="/de/transform" element={<RequireAuth><Layout><DataTransform /></Layout></RequireAuth>} />
        <Route path="/de/pipelines" element={<RequireAuth><Layout><DataPipelines /></Layout></RequireAuth>} />
        <Route path="/pred/forecast" element={<RequireAuth><Layout><Forecasting /></Layout></RequireAuth>} />
        <Route path="/pred/models" element={<RequireAuth><Layout><ModelManagement /></Layout></RequireAuth>} />
        <Route path="/pred/scenarios" element={<RequireAuth><Layout><ScenarioAnalysis /></Layout></RequireAuth>} />
        <Route path="/pred/performance" element={<RequireAuth><Layout><ModelPerformance /></Layout></RequireAuth>} />
        <Route path="/agents" element={<RequireAuth><Layout><AgentDashboard /></Layout></RequireAuth>} />
        <Route path="/agents/status" element={<RequireAuth><Layout><AgentStatus /></Layout></RequireAuth>} />
        <Route path="/agents/history" element={<RequireAuth><Layout><TaskHistory /></Layout></RequireAuth>} />
        <Route path="/agents/graph" element={<RequireAuth><Layout><ExecutionGraph /></Layout></RequireAuth>} />
        <Route path="/agents/logs" element={<RequireAuth><Layout><AgentLogs /></Layout></RequireAuth>} />
        <Route path="/agents/memory" element={<RequireAuth><Layout><MemoryViewer /></Layout></RequireAuth>} />
        <Route path="/workflows" element={<RequireAuth><Layout><Workflows /></Layout></RequireAuth>} />
        <Route path="/workflows/builder" element={<RequireAuth><Layout><WorkflowBuilder /></Layout></RequireAuth>} />
        <Route path="/workflows/templates" element={<RequireAuth><Layout><WorkflowTemplates /></Layout></RequireAuth>} />
        <Route path="/workflows/:id" element={<RequireAuth><Layout><WorkflowDetails /></Layout></RequireAuth>} />
        <Route path="/workflows/:id/history" element={<RequireAuth><Layout><WorkflowHistory /></Layout></RequireAuth>} />
        <Route path="/workflows/executions/:executionId" element={<RequireAuth><Layout><WorkflowExecutionDetails /></Layout></RequireAuth>} />
        <Route path="/workflows/approvals" element={<RequireAuth><Layout><WorkflowApprovals /></Layout></RequireAuth>} />
        <Route path="/knowledge" element={<RequireAuth><Layout><KnowledgeBase /></Layout></RequireAuth>} />
        <Route path="/knowledge/documents" element={<RequireAuth><Layout><KnowledgeDocuments /></Layout></RequireAuth>} />
        <Route path="/knowledge/documents/:id" element={<RequireAuth><Layout><KnowledgeDocumentDetail /></Layout></RequireAuth>} />
        <Route path="/knowledge/upload" element={<RequireAuth><Layout><KnowledgeUpload /></Layout></RequireAuth>} />
        <Route path="/knowledge/collections" element={<RequireAuth><Layout><KnowledgeCollections /></Layout></RequireAuth>} />
        <Route path="/knowledge/search" element={<RequireAuth><Layout><KnowledgeSearch /></Layout></RequireAuth>} />
        <Route path="/knowledge/rag" element={<RequireAuth><Layout><KnowledgeRAGChat /></Layout></RequireAuth>} />
        <Route path="/mlops" element={<RequireAuth><Layout><MLOps /></Layout></RequireAuth>} />
        <Route path="/mlops/models" element={<RequireAuth><Layout><MLOpsModels /></Layout></RequireAuth>} />
        <Route path="/mlops/models/:id" element={<RequireAuth><Layout><MLOpsModelDetail /></Layout></RequireAuth>} />
        <Route path="/mlops/experiments" element={<RequireAuth><Layout><MLOpsExperiments /></Layout></RequireAuth>} />
        <Route path="/mlops/training" element={<RequireAuth><Layout><MLOpsTraining /></Layout></RequireAuth>} />
        <Route path="/mlops/deployments" element={<RequireAuth><Layout><MLOpsDeployments /></Layout></RequireAuth>} />
        <Route path="/mlops/monitoring" element={<RequireAuth><Layout><MLOpsMonitoring /></Layout></RequireAuth>} />
        <Route path="/mlops/drift" element={<RequireAuth><Layout><MLOpsDrift /></Layout></RequireAuth>} />
        <Route path="/governance" element={<RequireAuth><Layout><Governance /></Layout></RequireAuth>} />
        <Route path="/governance/policies" element={<RequireAuth><Layout><GovernancePolicies /></Layout></RequireAuth>} />
        <Route path="/governance/security" element={<RequireAuth><Layout><GovernanceSecurity /></Layout></RequireAuth>} />
        <Route path="/governance/classifications" element={<RequireAuth><Layout><GovernanceClassifications /></Layout></RequireAuth>} />
        <Route path="/health" element={<RequireAuth><Layout><Health /></Layout></RequireAuth>} />
        <Route path="/metrics" element={<RequireAuth><Layout><Metrics /></Layout></RequireAuth>} />
        <Route path="/audit" element={<RequireAuth><Layout><Audit /></Layout></RequireAuth>} />
        <Route path="/alerts" element={<RequireAuth><Layout><Alerts /></Layout></RequireAuth>} />
        <Route path="/jobs" element={<RequireAuth><Layout><Jobs /></Layout></RequireAuth>} />
        <Route path="/flags" element={<RequireAuth><Layout><Flags /></Layout></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><Layout><Settings /></Layout></RequireAuth>} />
        <Route path="/organization" element={<RequireAuth><Layout><TenantOrganization /></Layout></RequireAuth>} />
        <Route path="/organization/usage" element={<RequireAuth><Layout><TenantUsage /></Layout></RequireAuth>} />
        <Route path="/organization/api-keys" element={<RequireAuth><Layout><TenantApiKeys /></Layout></RequireAuth>} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
