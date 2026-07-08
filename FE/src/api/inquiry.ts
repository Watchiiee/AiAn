import { apiGet, apiPost, apiPatch } from "./client";
import type {
  InquiryRequest,
  InquiryCreateResponse,
  MyInquiry,
  PendingInquiry,
  ReviewRequest,
  ReviewResponse,
  RuleUpdateRequest,
  RuleUpdateResponse,
} from "../types/inquiry";

/**
 * 민원 문의 한 건을 등록한다.
 * v3부터는 답변을 바로 안 준다 — 접수 확인(id)만 온다.
 * 담당자 검토·승인 후에야 /api/inquiry/my 에서 답변을 볼 수 있다.
 */
export function postInquiry(text: string): Promise<InquiryCreateResponse> {
  const body: InquiryRequest = { text };
  return apiPost<InquiryRequest, InquiryCreateResponse>("/api/inquiry", body);
}

/** 로그인한 사용자 본인이 등록한 문의 목록. 검색 없이 토큰만으로 자동 필터링. */
export function getMyInquiries(): Promise<MyInquiry[]> {
  return apiGet<MyInquiry[]>("/api/inquiry/my");
}

/** 내 문의 상세 1건. 본인 것이 아니면 404. */
export function getMyInquiryDetail(id: number): Promise<MyInquiry> {
  return apiGet<MyInquiry>(`/api/inquiry/my/${id}`);
}

/** 담당자 전용 — 검토 대기 목록. 일반 사용자 토큰이면 403. */
export function getPendingInquiries(): Promise<PendingInquiry[]> {
  return apiGet<PendingInquiry[]>("/api/inquiry/pending");
}

/**
 * 담당자 전용 — 검토·승인.
 * finalAnswer 를 null 로 보내면 AI 초안 그대로 승인, 텍스트를 보내면 그 내용으로 교체해서 승인.
 */
export function reviewInquiry(
  id: number,
  finalAnswer: string | null,
): Promise<ReviewResponse> {
  const body: ReviewRequest = { final_answer: finalAnswer };
  return apiPatch<ReviewRequest, ReviewResponse>(`/api/inquiry/${id}/review`, body);
}

/**
 * 담당자 전용(master만) — 부서/우선순위 재배정.
 * 하나만 보내면 그 필드만 바뀐다. staff 계정으로 호출하면 403.
 */
export function updateInquiryRule(
  id: number,
  patch: RuleUpdateRequest,
): Promise<RuleUpdateResponse> {
  return apiPatch<RuleUpdateRequest, RuleUpdateResponse>(
    `/api/inquiry/${id}/rule`,
    patch,
  );
}
