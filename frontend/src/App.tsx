import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import LLMPage from "./pages/LLMPage";
import AgentsPage from "./pages/AgentsPage";
import CodingPage from "./pages/CodingPage";
import AutomationPage from "./pages/AutomationPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/llm" element={<LLMPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/coding" element={<CodingPage />} />
        <Route path="/automation" element={<AutomationPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
