import { Routes, Route, Navigate } from "react-router-dom";
import Header from "./components/Header";
import CitizenPage from "./pages/CitizenPage";
import StaffPage from "./pages/StaffPage";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-[#eef2f7] text-[#0f172a]">
      <Header />
      <Routes>
        <Route path="/" element={<CitizenPage />} />
        <Route path="/admin" element={<StaffPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
