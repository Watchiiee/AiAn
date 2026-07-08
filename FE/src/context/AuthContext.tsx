import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { AuthSession, Role } from "../types/auth";
import {
  getSession,
  setSession as persistSession,
  clearSession,
  UNAUTHORIZED_EVENT,
} from "../lib/authStorage";

interface AuthContextValue {
  session: AuthSession | null;
  role: Role | null;
  isAuthenticated: boolean;
  /** 세션 만료로 강제 로그아웃된 경우 true (로그인 화면에 안내 문구 표시용) */
  expired: boolean;
  login: (session: AuthSession) => void;
  logout: () => void;
  clearExpiredFlag: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<AuthSession | null>(() =>
    getSession(),
  );
  const [expired, setExpired] = useState(false);

  useEffect(() => {
    // client.ts 가 401 을 받으면 이 이벤트를 쏜다 -> 자동 로그아웃 처리
    function handleUnauthorized() {
      setSessionState(null);
      setExpired(true);
    }
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () =>
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  }, []);

  function login(newSession: AuthSession) {
    persistSession(newSession);
    setSessionState(newSession);
    setExpired(false);
  }

  function logout() {
    clearSession();
    setSessionState(null);
  }

  const value: AuthContextValue = {
    session,
    role: session?.role ?? null,
    isAuthenticated: session !== null,
    expired,
    login,
    logout,
    clearExpiredFlag: () => setExpired(false),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 는 AuthProvider 안에서만 쓸 수 있어요.");
  return ctx;
}
