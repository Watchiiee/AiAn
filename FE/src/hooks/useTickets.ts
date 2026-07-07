import { useQuery } from "@tanstack/react-query";
import { MOCK_TICKETS } from "../mock/tickets";
import type { Ticket } from "../types/inquiry";

/**
 * 담당자 인박스 목록.
 * 지금은 목업을 반환한다. 백엔드에 목록 조회 API 가 생기면
 * queryFn 을 fetch 로 바꾸기만 하면 된다. 예:
 *
 *   queryFn: () => apiGet<Ticket[]>("/api/inquiries")
 */
export function useTickets() {
  return useQuery<Ticket[]>({
    queryKey: ["tickets"],
    queryFn: async () => {
      // 실제 네트워크 느낌을 위해 살짝 지연 (원하면 제거)
      await new Promise((r) => setTimeout(r, 200));
      return MOCK_TICKETS;
    },
  });
}
