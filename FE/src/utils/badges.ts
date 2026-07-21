import type { Priority, RecordStatus, InquiryType, AnswerConfidence } from "../types/inquiry";
import { WEAK_SCORE_THRESHOLD } from "../constants/options";

// 디자인의 색상 규칙을 Tailwind 클래스로 옮긴 헬퍼들.
// 정확한 브랜드 색을 맞추려고 일부는 arbitrary value(#hex)를 사용한다.

/** 우선순위 배지 (칩 형태, 점 포함) */
export function priorityBadgeClass(p: Priority): string {
  const base =
    "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-extrabold border";
  switch (p) {
    case "긴급":
      return `${base} bg-[#fef2f2] text-[#dc2626] border-[#fecaca]`;
    case "높음":
      return `${base} bg-[#fff7ed] text-[#ea580c] border-[#fed7aa]`;
    case "보통":
      return `${base} bg-[#f1f5f9] text-[#475569] border-[#e2e8f0]`;
  }
}

/** 우선순위 점 색 */
export function priorityDotClass(p: Priority): string {
  const base = "inline-block h-1.5 w-1.5 rounded-full";
  switch (p) {
    case "긴급":
      return `${base} bg-[#dc2626]`;
    case "높음":
      return `${base} bg-[#ea580c]`;
    case "보통":
      return `${base} bg-[#94a3b8]`;
  }
}

/** 문의 처리 상태 배지 (사용자 쪽: 답변 대기중 / 답변 완료) */
export function recordStatusBadgeClass(s: RecordStatus): string {
  const base =
    "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-extrabold border";
  return s === "answered"
    ? `${base} bg-[#f0fdf4] text-[#16a34a] border-[#bbf7d0]`
    : `${base} bg-[#fffbeb] text-[#d97706] border-[#fde68a]`;
}

export function recordStatusLabel(s: RecordStatus): string {
  return s === "answered" ? "답변 완료" : "답변 대기중";
}

/** 유형 배지 (기본 회색 톤. 긴급/오류 계열만 살짝 강조) */
export function typeBadgeClass(type: InquiryType, size: "sm" | "lg" = "sm"): string {
  const pad = size === "lg" ? "px-2.5 py-1 text-xs" : "px-2 py-0.5 text-[11px]";
  const base = `inline-flex items-center rounded-md font-bold border ${pad}`;
  if (type === "긴급문의" || type === "오류·장애") {
    return `${base} bg-[#fef2f2] text-[#dc2626] border-[#fecaca]`;
  }
  if (type === "미분류") {
    return `${base} bg-[#f8fafc] text-[#94a3b8] border-[#e2e8f0]`;
  }
  return `${base} bg-[#f1f5f9] text-[#475569] border-[#e2e8f0]`;
}

/** 유사도 점수 배지 (RAG 근거 문서용) */
export function scoreBadgeClass(score: number): string {
  const weak = score <= WEAK_SCORE_THRESHOLD;
  const base =
    "flex-none rounded-md px-2 py-0.5 text-[11px] font-extrabold border";
  return weak
    ? `${base} bg-[#fffbeb] text-[#d97706] border-[#fde68a]`
    : `${base} bg-[#f0fdf4] text-[#16a34a] border-[#bbf7d0]`;
}

export function isWeakScore(score: number): boolean {
  return score <= WEAK_SCORE_THRESHOLD;
}

/** "부서변경 요청됨" 배지. 다른 배지들과 안 헷갈리게 보라 계열로. */
export function deptChangeBadgeClass(): string {
  return "inline-flex items-center gap-1 rounded-md border border-[#c4b5fd] bg-[#f5f3ff] px-2 py-0.5 text-[11px] font-extrabold text-[#7c3aed]";
}

/** 답변이 근거로 얼마나 뒷받침되는지 (sufficient/partial/insufficient) — 담당자 검토용 */
export function answerConfidenceLabel(v: AnswerConfidence): string {
  switch (v) {
    case "sufficient":
      return "✅ 근거 확실";
    case "partial":
      return "⚠️ 확인 필요";
    case "insufficient":
      return "❓ 근거 부족";
  }
}

export function answerConfidenceBadgeClass(v: AnswerConfidence): string {
  const base =
    "inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-extrabold border";
  switch (v) {
    case "sufficient":
      return `${base} bg-[#f0fdf4] text-[#16a34a] border-[#bbf7d0]`;
    case "partial":
      return `${base} bg-[#fffbeb] text-[#d97706] border-[#fde68a]`;
    case "insufficient":
      return `${base} bg-[#f8fafc] text-[#64748b] border-[#e2e8f0]`;
  }
}
