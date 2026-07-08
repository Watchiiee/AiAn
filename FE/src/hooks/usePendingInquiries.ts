import { useQuery } from "@tanstack/react-query";
import { getPendingInquiries } from "../api/inquiry";
import type { PendingInquiry } from "../types/inquiry";

/** 담당자 전용 — 검토 대기 목록 */
export function usePendingInquiries() {
  return useQuery<PendingInquiry[]>({
    queryKey: ["pendingInquiries"],
    queryFn: getPendingInquiries,
  });
}
