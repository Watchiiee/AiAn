// 백엔드 응답 스펙 (v3 기준 — 문의 등록/조회 구조 변경 반영)
//
// 흐름:
//   사용자: POST /api/inquiry (등록)          -> 접수 확인만 받음 (답변 내용 모름)
//   사용자: GET  /api/inquiry/my (내 문의함)   -> 로그인 기반 자동 필터링, 검토 끝난 건만 답변 보임
//   담당자: GET  /api/inquiry/pending (검토 대기) -> AI 초안 + 확신도 확인
//   담당자: PATCH /api/inquiry/{id}/review     -> 그대로 승인 또는 수정 후 승인

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

/** 사용자 쪽에서 보이는 문의 처리 상태 (담당자 검토 전/후) */
export type RecordStatus = "pending" | "answered";

/** 답변이 근거로 얼마나 뒷받침되는지 (담당자 검토용) */
export type AnswerConfidence = "sufficient" | "partial" | "insufficient";

/** POST /api/inquiry 의 요청 바디 */
export interface InquiryRequest {
  text: string;
}

/** POST /api/inquiry 의 응답 바디. 이제 접수 확인만 온다 (답변은 안 옴). */
export interface InquiryCreateResponse {
  id: number;
  message: string;
  created_at: string;
}

/**
 * GET /api/inquiry/my, GET /api/inquiry/my/{id} 의 응답.
 * status가 "pending"이면 answer는 항상 null.
 */
export interface MyInquiry {
  id: number;
  created_at: string;
  original_text: string;
  department: string;
  priority: Priority;
  status: RecordStatus;
  answer: string | null;
}

/**
 * GET /api/inquiry/pending 의 응답 (담당자 전용).
 * AI 초안·확신도가 포함된다. RAG 근거문서나 분류 확신도는 이 API에 없다.
 */
export interface PendingInquiry {
  id: number;
  created_at: string;
  original_text: string;
  inquiry_type: InquiryType;
  department: string;
  priority: Priority;
  answer_draft: string;
  answer_confidence: AnswerConfidence;
}

/** PATCH /api/inquiry/{id}/review 의 요청 바디 */
export interface ReviewRequest {
  /** null(또는 생략)이면 AI 초안 그대로 승인, 값이 있으면 그 내용으로 교체해서 승인 */
  final_answer: string | null;
}

/** PATCH /api/inquiry/{id}/review 의 응답. GET /api/inquiry/my 항목과 같은 형식. */
export type ReviewResponse = MyInquiry;
