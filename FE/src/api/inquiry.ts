import { apiPost } from "./client";
import type { InquiryRequest, InquiryResponse } from "../types/inquiry";

/**
 * 민원 문의 한 건을 백엔드로 보낸다.
 * 백엔드가 분류 → 룰 → RAG → 답변초안을 처리해 JSON 으로 돌려준다.
 * 주의: LLM 이 실패해도 서버는 200 으로 응답하며 llm_error 에 사유가 담긴다.
 */
export function postInquiry(text: string): Promise<InquiryResponse> {
  const body: InquiryRequest = { text };
  return apiPost<InquiryRequest, InquiryResponse>("/api/inquiry", body);
}
