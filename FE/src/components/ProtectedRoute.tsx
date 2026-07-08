import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../types/auth";
import { homePathForRole } from "../utils/roleRoute";

interface ProtectedRouteProps {
  children: ReactNode;
  /** 지정하면 해당 role만 접근 가능. 다른 role 이면 자기 홈으로 리다이렉트 */
  allow?: Role[];
}

export default function ProtectedRoute({ children, allow }: ProtectedRouteProps) {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated || !role) {
    return <Navigate to="/login" replace />;
  }

  if (allow && !allow.includes(role)) {
    return <Navigate to={homePathForRole(role)} replace />;
  }

  return <>{children}</>;
}
