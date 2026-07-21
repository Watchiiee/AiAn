import { LOW_CONFIDENCE_THRESHOLD } from "../constants/options";

/** 확신도가 낮은지 (분류 불확실 표시용) */
export function isLowConfidence(confidence: number): boolean {
  return confidence < LOW_CONFIDENCE_THRESHOLD;
}

/** 확신도 % 값 */
export function confidencePercent(confidence: number): number {
  return Math.round(confidence * 100);
}

/** 확신도 막대/글자 색 */
export function confidenceColor(confidence: number): string {
  if (confidence >= 0.7) return "#16a34a";
  if (confidence >= LOW_CONFIDENCE_THRESHOLD) return "#d97706";
  return "#dc2626";
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
