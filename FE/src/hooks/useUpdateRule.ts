import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateInquiryRule } from "../api/inquiry";
import type { RuleUpdateResponse, Priority, PendingInquiry } from "../types/inquiry";

interface UpdateRuleInput {
  id: number;
  priority?: Priority;
  department?: string;
}

/**
 * master 전용 — 부서/우선순위 재배정.
 * v4 델타: 응답이 PendingInquiry(전체 정보)로 오므로, 다시 불러오지 않고
 * 그 응답으로 캐시의 해당 항목만 바로 교체한다 (재조회 없이 즉시 반영).
 */
export function useUpdateRule() {
  const queryClient = useQueryClient();

  return useMutation<RuleUpdateResponse, Error, UpdateRuleInput>({
    mutationFn: ({ id, priority, department }) =>
      updateInquiryRule(id, { priority, department }),
    onSuccess: (updated) => {
      queryClient.setQueryData<PendingInquiry[]>(["pendingInquiries"], (old) =>
        old?.map((item) => (item.id === updated.id ? updated : item)),
      );
    },
  });
}
