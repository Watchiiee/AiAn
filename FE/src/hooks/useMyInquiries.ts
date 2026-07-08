import { useQuery } from "@tanstack/react-query";
import { getMyInquiries } from "../api/inquiry";
import type { MyInquiry } from "../types/inquiry";

/** 로그인한 사용자 본인의 문의 목록. 검색 없이 토큰 기반으로 자동 필터링된다. */
export function useMyInquiries() {
  return useQuery<MyInquiry[]>({
    queryKey: ["myInquiries"],
    queryFn: getMyInquiries,
  });
}
