import { Routes, Route, Navigate } from "react-router-dom";
import Header from "./components/Header";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import CitizenPage from "./pages/CitizenPage";
import StaffPage from "./pages/StaffPage";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-[#eef2f7] text-[#0f172a]">
      <Header />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* 일반 사용자 화면 */}
        <Route
          path="/"
          element={
            <ProtectedRoute allow={["general"]}>
              <CitizenPage />
            </ProtectedRoute>
          }
        />

        {/* 담당자(관리자) 화면 */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allow={["staff"]}>
              <StaffPage />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
