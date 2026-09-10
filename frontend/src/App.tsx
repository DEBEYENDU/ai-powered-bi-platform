import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components";
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
import { Flags } from "./pages/Flags";
import { Forecasting } from "./pages/Forecasting";
import { Health } from "./pages/Health";
import { Jobs } from "./pages/Jobs";
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
