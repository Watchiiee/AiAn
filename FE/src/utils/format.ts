import type { Ticket } from "../types/inquiry";
import { PRIORITY_RANK, LOW_CONFIDENCE_THRESHOLD } from "../constants/options";

/** 접수번호 생성 (예: AiAn-20260707-0042). 백엔드가 발급하기 전 임시로 프론트에서 만든다. */
export function generateTicketNo(): string {
  const now = new Date();
  const ymd =
    now.getFullYear().toString() +
    String(now.getMonth() + 1).padStart(2, "0") +
    String(now.getDate()).padStart(2, "0");
  const seq = String(Math.floor(1000 + Math.random() * 9000));
  return `AiAn-${ymd}-${seq}`;
}

/** 확신도가 낮은지 (분류 불확실 표시용) */
export function isLowConfidence(confidence: number): boolean {
  return confidence < LOW_CONFIDENCE_THRESHOLD;
}

/** 확신도 % 문자열 */
export function confidencePercent(confidence: number): number {
  return Math.round(confidence * 100);
}

/** 확신도 막대/글자 색 */
export function confidenceColor(confidence: number): string {
  if (confidence >= 0.7) return "#16a34a";
  if (confidence >= LOW_CONFIDENCE_THRESHOLD) return "#d97706";
  return "#dc2626";
}

/** 긴급 우선 정렬 */
export function sortByPriority(tickets: Ticket[]): Ticket[] {
  return [...tickets].sort(
    (a, b) => PRIORITY_RANK[a.rule.priority] - PRIORITY_RANK[b.rule.priority],
  );
}
