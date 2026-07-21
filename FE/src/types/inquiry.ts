// 백엔드 응답 스펙 (v4 기준 — 검토 화면 데이터 확장 + 권한 3단계)
//
// 흐름:
//   사용자: POST /api/inquiry (등록)          -> 접수 확인만 받음 (답변 내용 모름)
//   사용자: GET  /api/inquiry/my (내 문의함)   -> 로그인 기반 자동 필터링, 검토 끝난 건만 답변 보임
//   담당자(staff+): GET /api/inquiry/pending   -> 분류·근거문서·AI 초안·확신도 전부 확인
//   담당자(staff+): PATCH /api/inquiry/{id}/review -> 그대로 승인 또는 수정 후 승인
//   최고관리자(master만): PATCH /api/inquiry/{id}/rule -> 부서/우선순위 재배정
//
// 권한: general < staff < master (계층형. master는 staff가 하는 것도 다 가능)

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

/** "admin"(행정) 또는 "technical"(기술질의) */
export type InquiryDomain = "admin" | "technical";

/** RAG 검색으로 찾은 근거 문서 한 건 */
export interface RetrievedDoc {
  content: string;
  /** "파일명 > 질문" 형태의 출처 */
  source: string;
  /** 유사도 점수. 0.4 이하면 "근거 약함" */
  score: number;
  /** AI가 이 문서를 실제로 답변 생성에 사용했는지. 기본값 true */
  selected: boolean;
}

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
 * GET /api/inquiry/pending 의 응답 (staff 이상 전용).
 * v4에서 분류·근거문서·LLM 실패 여부가 전부 복원되었다.
 */
export interface PendingInquiry {
  id: number;
  created_at: string;
  original_text: string;
  inquiry_type: InquiryType;
  /** 핵심 요청 한 줄 요약 */
  key_request: string;
  /** 분류 확신도 0~1. 0.5 미만이면 "분류 불확실" 표시 */
  confidence: number;
  domain: InquiryDomain;
  department: string;
  priority: Priority;
  answer_draft: string;
  answer_confidence: AnswerConfidence;
  retrieved: RetrievedDoc[];
  used_llm: boolean;
  /** null 이면 정상, 값이 있으면 LLM 생성 실패 */
  llm_error: string | null;

  // v4 델타 — staff의 부서변경 요청 표시. master가 /rule 로 재배정하면
  // 서버가 이 4개를 자동으로 초기화한다 (프론트에서 따로 지울 필요 없음).
  /** staff가 부서변경을 요청했는지 */
  dept_change_requested: boolean;
  dept_change_reason: string | null;
  dept_change_suggested: string | null;
  /** 요청한 staff의 이메일 */
  dept_change_requested_by: string | null;
}

/** PATCH /api/inquiry/{id}/review 의 요청 바디 */
export interface ReviewRequest {
  /** null(또는 생략)이면 AI 초안 그대로 승인, 값이 있으면 그 내용으로 교체해서 승인 */
  final_answer: string | null;
}

/** PATCH /api/inquiry/{id}/review 의 응답. GET /api/inquiry/my 항목과 같은 형식. */
export type ReviewResponse = MyInquiry;

/**
 * PATCH /api/inquiry/{id}/rule 의 요청 바디 (master 전용).
 * 둘 다 선택 필드 — 하나만 보내면 그것만 바뀐다.
 */
export interface RuleUpdateRequest {
  priority?: Priority;
  department?: string;
}

/**
 * PATCH /api/inquiry/{id}/rule 의 응답.
 * ⚠️ v4 델타에서 바뀜: 이전엔 MyInquiry(간단 정보)였는데, 이제는
 * PendingInquiry(분류·근거문서·confidence 등 전체 정보)로 온다.
 */
export type RuleUpdateResponse = PendingInquiry;

/** PATCH /api/inquiry/{id}/request-department-change 의 요청 바디 (staff 이상) */
export interface DeptChangeRequest {
  reason: string;
  /** 선택. 없으면 null */
  suggested_department?: string | null;
}

/** PATCH /api/inquiry/{id}/request-department-change 의 응답. /pending 항목과 동일. */
export type DeptChangeResponse = PendingInquiry;