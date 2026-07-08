// 백엔드 응답 스펙 (인수인계 문서 기준)
// POST /api/inquiry  ->  아래 InquiryResponse

export type InquiryType =
  | "경력인증"
  | "신청"
  | "변경"
  | "취소·환불"
  | "오류·장애"
  | "일반문의"
  | "긴급문의"
  | "미분류";

export type Priority = "긴급" | "높음" | "보통";

export type TicketStatus = "신규" | "검토중" | "발송완료";

export type AnswerConfidence = "sufficient" | "partial" | "insufficient";

export type InquiryDomain = "admin" | "technical";

export interface Classification {
  type: InquiryType;
  key_request: string;
  /** 0~1. 0.5 미만이면 "분류 불확실" 표시 */
  confidence: number;
  /** "admin"(행정) 또는 "technical"(기술질의). v2에서 추가됨 */
  domain: InquiryDomain;
}

export interface Rule {
  priority: Priority;
  department: string;
}

export interface RetrievedDoc {
  content: string;
  /** "파일명 > 질문" 형태의 출처 */
  source: string;
  /** 유사도 점수. 0.4 이하면 "근거 약함" */
  score: number;
}

/** POST /api/inquiry 의 요청 바디 */
export interface InquiryRequest {
  text: string;
}

/** POST /api/inquiry 의 응답 바디 */
export interface InquiryResponse {
  original_text: string;
  classification: Classification;
  rule: Rule;
  retrieved: RetrievedDoc[];
  answer_draft: string | null;
  /** 답변이 근거로 얼마나 뒷받침되는지. v2에서 추가됨 */
  answer_confidence: AnswerConfidence;
  used_llm: boolean;
  /** null 이면 정상, 값이 있으면 LLM 생성 실패 */
  llm_error: string | null;
}

/**
 * 담당자 인박스에서 다루는 한 건.
 * 백엔드가 아직 목록 조회 API를 제공하지 않아, 지금은 목업으로 채운다.
 * (백엔드에 GET /api/inquiries 가 생기면 이 타입으로 그대로 받으면 된다)
 */
export interface Ticket extends InquiryResponse {
  ticket_id: string;
  status: TicketStatus;
}
