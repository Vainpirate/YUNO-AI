import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/shared/Header";
import { ToastContainer } from "./components/shared/ToastContainer";
import { Dashboard }      from "./pages/Dashboard";
import { AgentManager }   from "./pages/AgentManager";
import { WorkflowStudio } from "./pages/WorkflowStudio";
import { Monitoring }     from "./pages/Monitoring";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/agents"    element={<AgentManager />} />
            <Route path="/workflows" element={<WorkflowStudio />} />
            <Route path="/monitor"   element={<Monitoring />} />
          </Routes>
        </main>
      </div>
      <ToastContainer />
    </BrowserRouter>
  );
}
