import { BrowserRouter, Route, Routes } from "react-router-dom";
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
import { Settings } from "./pages/Settings";
import { TaskHistory } from "./pages/TaskHistory";
import { Users } from "./pages/Users";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/users" element={<Users />} />
          <Route path="/orgs" element={<Organizations />} />
          <Route path="/roles" element={<Roles />} />
          <Route path="/dashboards" element={<Dashboards />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/ai" element={<AIAdmin />} />
          <Route path="/ai/chat" element={<AIChat />} />
          <Route path="/ai/ask" element={<AskYourData />} />
          <Route path="/ai/dashboard-gen" element={<AIDashboardGenerator />} />
          <Route path="/ai/insights" element={<BusinessInsights />} />
          <Route path="/ai/reports" element={<ReportsLibrary />} />
          <Route path="/de/sources" element={<DataSources />} />
          <Route path="/de/quality" element={<DataQuality />} />
          <Route path="/de/cleaning" element={<DataCleaning />} />
          <Route path="/de/transform" element={<DataTransform />} />
          <Route path="/de/pipelines" element={<DataPipelines />} />
          <Route path="/pred/forecast" element={<Forecasting />} />
          <Route path="/pred/models" element={<ModelManagement />} />
          <Route path="/pred/scenarios" element={<ScenarioAnalysis />} />
          <Route path="/pred/performance" element={<ModelPerformance />} />
          <Route path="/agents" element={<AgentDashboard />} />
          <Route path="/agents/status" element={<AgentStatus />} />
          <Route path="/agents/history" element={<TaskHistory />} />
          <Route path="/agents/graph" element={<ExecutionGraph />} />
          <Route path="/agents/logs" element={<AgentLogs />} />
          <Route path="/agents/memory" element={<MemoryViewer />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/workflows/builder" element={<WorkflowBuilder />} />
          <Route path="/workflows/templates" element={<WorkflowTemplates />} />
          <Route path="/workflows/:id" element={<WorkflowDetails />} />
          <Route path="/workflows/:id/history" element={<WorkflowHistory />} />
          <Route path="/workflows/executions/:executionId" element={<WorkflowExecutionDetails />} />
          <Route path="/workflows/approvals" element={<WorkflowApprovals />} />
          <Route path="/health" element={<Health />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/flags" element={<Flags />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
