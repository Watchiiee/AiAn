import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateInquiryRule } from "../api/inquiry";
import type { RuleUpdateResponse, Priority } from "../types/inquiry";

interface UpdateRuleInput {
  id: number;
  priority?: Priority;
  department?: string;
}

/**
 * master 전용 — 부서/우선순위 재배정.
 * 성공하면 pending 목록을 새로고침해서 바뀐 값을 반영한다.
 */
export function useUpdateRule() {
  const queryClient = useQueryClient();

  return useMutation<RuleUpdateResponse, Error, UpdateRuleInput>({
    mutationFn: ({ id, priority, department }) =>
      updateInquiryRule(id, { priority, department }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pendingInquiries"] });
    },
  });
}
