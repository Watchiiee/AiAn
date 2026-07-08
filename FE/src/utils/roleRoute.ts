import type { Role } from "../types/auth";

/**
 * 로그인 성공 / 잘못된 역할로 접근 시 보낼 각 역할의 기본 화면.
 * staff 와 master 는 둘 다 담당자 화면(/admin)으로 간다.
 * (화면 안에서 role 에 따라 재배정 UI 노출 여부만 갈린다)
 */
export function homePathForRole(role: Role): string {
  return role === "general" ? "/" : "/admin";
}
