export type Role = "general" | "staff";

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  id: number;
  email: string;
  role: Role; // 가입은 항상 "general" (서버가 강제)
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  role: Role;
}

/** 프론트에서 들고 다니는 로그인 세션 정보 (localStorage 저장 형태) */
export interface AuthSession {
  token: string;
  role: Role;
  email: string;
}
