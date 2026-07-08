import { apiPost } from "./client";
import type {
  RegisterRequest,
  RegisterResponse,
  LoginRequest,
  LoginResponse,
} from "../types/auth";

/** 회원가입. role 을 보내도 서버가 무시하고 항상 "general" 로 생성한다. */
export function registerUser(
  email: string,
  password: string,
): Promise<RegisterResponse> {
  const body: RegisterRequest = { email, password };
  return apiPost<RegisterRequest, RegisterResponse>("/api/auth/register", body, {
    auth: false,
  });
}

export function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const body: LoginRequest = { email, password };
  return apiPost<LoginRequest, LoginResponse>("/api/auth/login", body, {
    auth: false,
  });
}
