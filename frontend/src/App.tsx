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
import { Flags } from "./pages/Flags";
import { Health } from "./pages/Health";
import { Jobs } from "./pages/Jobs";
import { Metrics } from "./pages/Metrics";
import { Organizations } from "./pages/Organizations";
import { Overview } from "./pages/Overview";
import { Reports } from "./pages/Reports";
import { Roles } from "./pages/Roles";
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
