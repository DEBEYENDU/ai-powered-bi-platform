import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components";
import {
  Alerts,
  Audit,
  Flags,
  Health,
  Jobs,
  Metrics,
  Orgs,
  Overview,
  Roles,
  Settings,
  Users,
} from "./pages";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/users" element={<Users />} />
          <Route path="/orgs" element={<Orgs />} />
          <Route path="/roles" element={<Roles />} />
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
