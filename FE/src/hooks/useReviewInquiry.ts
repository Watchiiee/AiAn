import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reviewInquiry } from "../api/inquiry";
import type { ReviewResponse } from "../types/inquiry";

interface ReviewInput {
  id: number;
  /** null 이면 AI 초안 그대로 승인, 값이 있으면 그 내용으로 교체해서 승인 */
  finalAnswer: string | null;
}

/**
 * 담당자 승인 훅. 승인되면 그 건이 pending 목록에서 사라지므로
 * 성공 시 pendingInquiries 쿼리를 무효화해서 목록을 새로고침한다.
 */
export function useReviewInquiry() {
  const queryClient = useQueryClient();

  return useMutation<ReviewResponse, Error, ReviewInput>({
    mutationFn: ({ id, finalAnswer }) => reviewInquiry(id, finalAnswer),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pendingInquiries"] });
    },
  });
}
