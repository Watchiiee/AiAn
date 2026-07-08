import { PRIORITY_RANK } from "../constants/options";

/** 긴급 우선 정렬 (담당자 검토 대기 목록용) */
export function sortByPriority<T extends { priority: keyof typeof PRIORITY_RANK }>(
  items: T[],
): T[] {
  return [...items].sort(
    (a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority],
  );
}

/** "2026-07-08T14:10:29" 같은 ISO 문자열을 화면용으로 짧게 표시 */
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", {
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
