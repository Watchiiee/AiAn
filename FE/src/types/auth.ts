/**
 * 권한 3단계 (계층형): general < staff < master
 * master는 staff가 하는 것(검토 큐 조회, 답변 승인)도 다 할 수 있고,
 * 추가로 부서/우선순위 재배정(PATCH /api/inquiry/{id}/rule)을 할 수 있다.
 */
export type Role = "general" | "staff" | "master";

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
  /** staff의 소속 부서. master 계정은 항상 null (전체 부서를 다 보는 계정) */
  department: string | null;
}

/** 프론트에서 들고 다니는 로그인 세션 정보 (localStorage 저장 형태) */
export interface AuthSession {
  token: string;
  role: Role;
  email: string;
  /** staff의 소속 부서. master는 null */
  department: string | null;
}