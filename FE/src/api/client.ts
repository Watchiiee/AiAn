import { getToken, clearSession, dispatchUnauthorized } from "../lib/authStorage";

// 얇은 fetch 래퍼. baseURL 은 .env 의 VITE_API_BASE 로 바꿀 수 있다.
// 예) .env.development -> VITE_API_BASE=http://localhost:8000

const BASE_URL = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  /** 로그인/회원가입처럼 토큰이 필요 없는 요청이면 false */
  auth?: boolean;
}

async function request<TResponse>(
  path: string,
  init: RequestInit,
  { auth = true }: RequestOptions = {},
): Promise<TResponse> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (res.status === 401) {
    // 토큰이 없거나 만료됨. 세션 정리 + 전역 이벤트 발행 -> AuthProvider 가 로그아웃 처리.
    if (auth) {
      clearSession();
      dispatchUnauthorized();
    }
    const detail = await safeDetail(res);
    throw new ApiError(detail ?? "인증이 필요해요. 다시 로그인해 주세요.", 401, detail);
  }

  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new ApiError(
      detail ?? `요청에 실패했어요 (HTTP ${res.status})`,
      res.status,
      detail,
    );
  }

  return (await res.json()) as TResponse;
}

async function safeDetail(res: Response): Promise<string | undefined> {
  try {
    const body = await res.json();
    return typeof body?.detail === "string" ? body.detail : undefined;
  } catch {
    return undefined;
  }
}

export function apiPost<TBody, TResponse>(
  path: string,
  body: TBody,
  options?: RequestOptions,
): Promise<TResponse> {
  return request<TResponse>(
    path,
    { method: "POST", body: JSON.stringify(body) },
    options,
  );
}

export function apiGet<TResponse>(
  path: string,
  options?: RequestOptions,
): Promise<TResponse> {
  return request<TResponse>(path, { method: "GET" }, options);
}

export function apiPatch<TBody, TResponse>(
  path: string,
  body: TBody,
  options?: RequestOptions,
): Promise<TResponse> {
  return request<TResponse>(
    path,
    { method: "PATCH", body: JSON.stringify(body) },
    options,
  );
}