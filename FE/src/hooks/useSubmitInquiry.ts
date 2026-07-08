import { useMutation } from "@tanstack/react-query";
import { postInquiry } from "../api/inquiry";
import type { InquiryCreateResponse } from "../types/inquiry";

/**
 * 민원 문의 등록 훅.
 * v3부터 응답은 접수 확인(id)만 온다 — 답변 내용은 담당자 승인 후 /my 에서 봐야 한다.
 */
export function useSubmitInquiry() {
  return useMutation<InquiryCreateResponse, Error, string>({
    mutationFn: (text: string) => postInquiry(text),
  });
}
