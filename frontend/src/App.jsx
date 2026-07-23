import { Route, Routes } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import ComplaintDetailPage from "./pages/ComplaintDetailPage";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <div className="app">
      <Sidebar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/complaints/:id" element={<ComplaintDetailPage />} />
      </Routes>
    </div>
  );
}
