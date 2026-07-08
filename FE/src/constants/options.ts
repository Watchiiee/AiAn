/** 민원인 입력창 아래 예시 질문 칩 */
export const EXAMPLE_CHIPS = [
  "전기안전관리자 선임 안 하면 벌금 있나요?",
  "경력증명서 발급에 필요한 서류가 뭔가요?",
  "회원 정보(연락처)를 변경하고 싶어요",
  "자격증 발급 신청 중 오류가 났어요",
];

/** 담당자 검토 대기 인박스 — 우선순위 필터 */
export const PRIORITY_FILTERS = ["전체", "긴급", "높음", "보통"] as const;

/** 내 문의함 — 처리 상태 필터 */
export const MY_STATUS_FILTERS = ["전체", "답변 대기중", "답변 완료"] as const;

/** 긴급 우선 정렬 순서 */
export const PRIORITY_RANK: Record<"긴급" | "높음" | "보통", number> = {
  긴급: 0,
  높음: 1,
  보통: 2,
};
