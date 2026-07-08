import type { Ticket } from "../types/inquiry";

/**
 * 담당자 인박스 목업 데이터.
 * 백엔드에 목록 조회 API 가 아직 없어서 임시로 프론트에 둔다.
 * GET /api/inquiries 가 생기면 useTickets 훅에서 이 배열 대신 fetch 로 교체하면 된다.
 *
 * 데모용으로 다양한 케이스를 섞어둠:
 *  - 긴급 우선순위
 *  - 낮은 확신도(미분류, 0.43) + answer_confidence: partial
 *  - LLM 생성 실패(answer_draft: null, llm_error 존재) + answer_confidence: insufficient
 *  - 정상/검토중/발송완료 상태
 */
export const MOCK_TICKETS: Ticket[] = [
  {
    ticket_id: "AiAn-20260707-0051",
    original_text:
      "홈페이지에서 자격증 발급 신청하고 결제까지 다 했는데 오류나면서 신청이 안 됐어요. 접수 마감이 오늘까지인데 너무 급합니다!!",
    classification: {
      type: "오류·장애",
      key_request: "자격증 발급 신청 결제 완료 후 시스템 오류로 접수 실패",
      confidence: 0.87,
      domain: "admin",
    },
    rule: { priority: "긴급", department: "정보시스템팀" },
    retrieved: [
      {
        content:
          "결제는 완료되었으나 신청 건이 생성되지 않은 경우, 결제 로그를 기준으로 담당자가 수동 접수 처리하며 중복 결제는 발생하지 않습니다.",
        source: "knowledge_payment_error.md > Q. 결제 후 접수 실패",
        score: 0.742,
      },
      {
        content:
          "자격증 발급 접수 마감일에 시스템 장애가 확인된 경우 마감 시각은 장애 복구 시점까지 연장 처리됩니다.",
        source: "policy_deadline_extension.md > 2조",
        score: 0.611,
      },
    ],
    answer_draft:
      "안녕하세요. 결제는 정상 완료되었으나 신청 건이 생성되지 않은 것으로 확인됩니다. 결제 내역을 기준으로 담당자가 수동으로 접수 처리해 드리며, 중복 결제는 발생하지 않으니 안심하셔도 됩니다. 마감 관련해서도 시스템 오류가 확인되어 불이익이 없도록 조치하겠습니다.",
    answer_confidence: "sufficient",
    used_llm: true,
    llm_error: null,
    status: "신규",
  },
  {
    ticket_id: "AiAn-20260707-0042",
    original_text: "전기안전관리자 선임 안 하면 벌금 있어?",
    classification: {
      type: "일반문의",
      key_request: "전기안전관리자 미선임 시 벌금 문의",
      confidence: 0.9,
      domain: "admin",
    },
    rule: { priority: "보통", department: "민원안내팀" },
    retrieved: [
      {
        content:
          "전기안전관리자를 선임하지 않은 자는 500만원 이하의 벌금에 처할 수 있습니다.",
        source: "knowledge_electric_safety_manager.md > Q. 미선임 시 벌칙",
        score: 0.689,
      },
      {
        content:
          "전기안전관리자는 사업 개시 전 또는 전기설비 사용 전에 선임하여야 합니다.",
        source: "knowledge_electric_safety_manager.md > 선임 시기",
        score: 0.532,
      },
    ],
    answer_draft:
      "안녕하세요. 전기안전관리자를 선임하지 않은 경우 관련 법령에 따라 500만원 이하의 벌금이 부과될 수 있습니다. 전기설비 사용 전 반드시 선임하셔야 하며, 선임 절차가 필요하시면 안내해 드리겠습니다.",
    answer_confidence: "sufficient",
    used_llm: true,
    llm_error: null,
    status: "신규",
  },
  {
    ticket_id: "AiAn-20260707-0048",
    original_text: "그거 어떻게 하는거예요? 저번에 말한거요.",
    classification: {
      type: "미분류",
      key_request: "요청 내용이 불명확하여 추가 확인 필요",
      confidence: 0.43,
      domain: "admin",
    },
    rule: { priority: "보통", department: "민원안내팀" },
    retrieved: [
      {
        content:
          "문의 내용이 불충분한 경우 담당자는 민원인에게 구체적인 내용을 재요청할 수 있습니다.",
        source: "guide_ambiguous_inquiry.md > 재확인 절차",
        score: 0.312,
      },
    ],
    answer_draft:
      "안녕하세요. 문의 주신 내용만으로는 정확한 요청 사항을 파악하기 어렵습니다. 어떤 업무에 대한 문의이신지 조금 더 구체적으로 알려주시면 신속히 안내해 드리겠습니다.",
    answer_confidence: "partial",
    used_llm: true,
    llm_error: null,
    status: "검토중",
  },
  {
    ticket_id: "AiAn-20260707-0045",
    original_text:
      "경력증명서 발급받으려면 재직증명서랑 4대보험 가입내역서 둘 다 필요한가요? 아니면 하나만 있어도 되나요?",
    classification: {
      type: "경력인증",
      key_request: "경력증명서 발급 시 필요 서류 문의",
      confidence: 0.82,
      domain: "admin",
    },
    rule: { priority: "높음", department: "자격관리팀" },
    retrieved: [
      {
        content:
          "경력 인증을 위해서는 재직증명서와 4대보험 가입내역서를 모두 제출하여야 하며, 둘 중 하나만으로는 인정되지 않습니다.",
        source: "knowledge_career_certification.md > 제출 서류",
        score: 0.771,
      },
      {
        content:
          "프리랜서·개인사업자의 경우 위촉계약서 및 소득금액증명원으로 대체할 수 있습니다.",
        source: "knowledge_career_certification.md > 예외 사항",
        score: 0.523,
      },
    ],
    answer_draft: null,
    answer_confidence: "insufficient",
    used_llm: false,
    llm_error: "LLMTimeoutError: upstream 504 after 30000ms",
    status: "신규",
  },
  {
    ticket_id: "AiAn-20260707-0039",
    original_text:
      "회원 정보에서 소속 회사랑 연락처를 바꾸고 싶은데 어디서 수정하나요?",
    classification: {
      type: "변경",
      key_request: "회원정보(소속·연락처) 변경 방법 문의",
      confidence: 0.94,
      domain: "admin",
    },
    rule: { priority: "보통", department: "회원관리팀" },
    retrieved: [
      {
        content:
          "회원정보 변경은 홈페이지 로그인 후 [마이페이지 > 회원정보 수정]에서 직접 변경할 수 있습니다.",
        source: "knowledge_member_info.md > 정보 변경",
        score: 0.698,
      },
    ],
    answer_draft:
      "안녕하세요. 회원정보 변경은 홈페이지 로그인 후 [마이페이지 > 회원정보 수정] 메뉴에서 소속 회사와 연락처를 직접 변경하실 수 있습니다. 변경이 어려우시면 도와드리겠습니다.",
    answer_confidence: "sufficient",
    used_llm: true,
    llm_error: null,
    status: "발송완료",
  },
];
