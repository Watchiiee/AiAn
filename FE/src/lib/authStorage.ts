import type { AuthSession } from "../types/auth";

const STORAGE_KEY = "aian_auth";

/** 401(토큰 없음/만료)이 오면 API 클라이언트가 이 이벤트를 쏜다.
 *  AuthProvider 가 구독해서 자동 로그아웃 처리한다. */
export const UNAUTHORIZED_EVENT = "aian:unauthorized";

export function getSession(): AuthSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

export function setSession(session: AuthSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function getToken(): string | null {
  return getSession()?.token ?? null;
}

export function dispatchUnauthorized(): void {
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}
