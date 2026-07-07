import { useMutation } from "@tanstack/react-query";
import { postInquiry } from "../api/inquiry";
import type { InquiryResponse } from "../types/inquiry";

/**
 * 민원 문의 제출 훅.
 * 백엔드 호출이 수 초 걸리므로 isPending 으로 로딩 스피너를 띄운다.
 *
 * 참고: 민원인 화면에서는 AI 결과(answer_draft 등)를 보여주지 않는다.
 * 응답은 "정상 접수됐다"는 확인 용도로만 쓰고, 접수번호는 프론트에서 생성한다.
 */
export function useSubmitInquiry() {
  return useMutation<InquiryResponse, Error, string>({
    mutationFn: (text: string) => postInquiry(text),
  });
}
