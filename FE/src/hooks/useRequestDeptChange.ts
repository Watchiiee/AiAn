import { useMutation, useQueryClient } from "@tanstack/react-query";
import { requestDepartmentChange } from "../api/inquiry";
import type { DeptChangeResponse, PendingInquiry } from "../types/inquiry";

interface RequestDeptChangeInput {
  id: number;
  reason: string;
  suggestedDepartment: string | null;
}

/**
 * staff 이상 — "이 부서가 아닌 것 같다" 표시만 남긴다 (실제 재배정은 master가 함).
 * 응답이 전체 PendingInquiry라 재조회 없이 캐시의 해당 항목만 바로 교체한다.
 */
export function useRequestDeptChange() {
  const queryClient = useQueryClient();

  return useMutation<DeptChangeResponse, Error, RequestDeptChangeInput>({
    mutationFn: ({ id, reason, suggestedDepartment }) =>
      requestDepartmentChange(id, reason, suggestedDepartment),
    onSuccess: (updated) => {
      queryClient.setQueryData<PendingInquiry[]>(["pendingInquiries"], (old) =>
        old?.map((item) => (item.id === updated.id ? updated : item)),
      );
    },
  });
}
