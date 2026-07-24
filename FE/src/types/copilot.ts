/**
 * 담당자 코파일럿 (사이드바 대화형 도우미).
 * POST /api/inquiry/{id}/copilot 이 text/event-stream(SSE)으로 응답한다.
 * 백엔드는 매 요청을 독립적으로 처리하며 이전 대화를 기억하지 않는다(v1 범위).
 */

export interface CopilotRequest {
  question: string;
}

export type CopilotRole = "user" | "assistant";

export interface CopilotMessage {
  id: string;
  role: CopilotRole;
  content: string;
  /** assistant 메시지가 아직 스트리밍 중인지 (타이핑 표시용) */
  streaming?: boolean;
  /** 이 메시지(요청)가 실패했는지 — 재시도 버튼 표시용 */
  failed?: boolean;
}