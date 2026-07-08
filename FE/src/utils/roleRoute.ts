import type { Role } from "../types/auth";

/** 로그인 성공 / 잘못된 역할로 접근 시 보낼 각 역할의 기본 화면 */
export function homePathForRole(role: Role): string {
  return role === "staff" ? "/admin" : "/";
}
