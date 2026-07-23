import type { Priority } from "../types/inquiry";

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

/** master가 재배정할 때 고를 수 있는 우선순위 */
export const PRIORITY_OPTIONS: Priority[] = ["긴급", "높음", "보통"];

/** master가 재배정할 때 고를 수 있는 부서 (실제 조직 부서 목록) */
export const DEPT_OPTIONS = [
  "안전관리지원팀",
  "설계감리지원팀",
  "회원관리팀",
  "공제운영팀",
  "교육원(교육운영팀)",
  "교육원(인적자원개발팀)",
  "정보전략실",
  "연구원",
  "경영지원팀",
];

/** 분류 확신도가 이 값 미만이면 "분류 불확실" */
export const LOW_CONFIDENCE_THRESHOLD = 0.5;

/** 유사도가 이 값 이하이면 "근거 약함" */
export const WEAK_SCORE_THRESHOLD = 0.4;