import type { PendingInquiry, Priority } from "../../types/inquiry";
import { formatDateTime } from "../../utils/format";
import LlmErrorBanner from "./LlmErrorBanner";
import ClassificationCard from "./ClassificationCard";
import RuleCard from "./RuleCard";
import DraftEditor from "./DraftEditor";
import EvidenceList from "./EvidenceList";

interface TicketDetailProps {
  inquiry: PendingInquiry;
  draft: string;
  onDraftChange: (v: string) => void;
  onApproveAsIs: () => void;
  onApproveEdited: () => void;
  isSubmitting: boolean;
  toast: string | null;

  /** master 전용 재배정 */
  canReassign: boolean;
  onSaveRule: (priority: Priority, department: string) => void;
  isSavingRule: boolean;

  /** staff 이상 — "이 부서 아닌 것 같다" 요청 */
  onRequestDeptChange: (reason: string, suggestedDepartment: string | null) => void;
  isRequestingDeptChange: boolean;

  /** AI 코파일럿 사이드바 토글 */
  copilotOpen: boolean;
  onToggleCopilot: () => void;
}

export default function TicketDetail({
  inquiry,
  draft,
  onDraftChange,
  onApproveAsIs,
  onApproveEdited,
  isSubmitting,
  toast,
  canReassign,
  onSaveRule,
  isSavingRule,
  onRequestDeptChange,
  isRequestingDeptChange,
  copilotOpen,
  onToggleCopilot,
}: TicketDetailProps) {
  const edited = draft.trim() !== inquiry.answer_draft.trim();

  return (
    <div className="mx-auto max-w-[820px] px-[30px] pb-10 pt-[26px]">
      {inquiry.llm_error && <LlmErrorBanner error={inquiry.llm_error} />}

      <div className="mb-1.5 flex items-center gap-2.5">
        <span className="font-mono text-[12.5px] font-semibold text-[#94a3b8]">
          #{inquiry.id}
        </span>
        <span className="text-[12px] font-semibold text-[#94a3b8]">
          {formatDateTime(inquiry.created_at)}
        </span>
        <span className="flex-1" />
        <button
          type="button"
          onClick={onToggleCopilot}
          className={[
            "rounded-[9px] border px-3 py-1.5 text-[12px] font-bold transition-colors",
            copilotOpen
              ? "border-[#2563eb] bg-[#eff6ff] text-[#2563eb]"
              : "border-[#e2e8f0] bg-white text-[#64748b] hover:bg-[#f8fafc]",
          ].join(" ")}
        >
          🤖 AI에게 물어보기
        </button>
      </div>

      <div className="mb-4 rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
        <div className="mb-[9px] text-[11.5px] font-bold text-[#94a3b8]">
          민원 원문
        </div>
        <p className="text-[15px] leading-relaxed text-[#1e293b]">
          {inquiry.original_text}
        </p>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <ClassificationCard
          inquiryType={inquiry.inquiry_type}
          keyRequest={inquiry.key_request}
          confidence={inquiry.confidence}
          domain={inquiry.domain}
        />
        <RuleCard
          inquiry={inquiry}
          canReassign={canReassign}
          onSaveRule={onSaveRule}
          isSavingRule={isSavingRule}
          onRequestDeptChange={onRequestDeptChange}
          isRequestingDeptChange={isRequestingDeptChange}
        />
      </div>

      <div className="mb-4">
        <DraftEditor
          value={draft}
          answerConfidence={inquiry.answer_confidence}
          onChange={onDraftChange}
        />
      </div>

      <div className="mb-4">
        <EvidenceList retrieved={inquiry.retrieved} />
      </div>

      <div className="sticky bottom-0 flex flex-wrap items-center gap-2.5 bg-gradient-to-t from-[#eef2f7] from-70% to-transparent pb-1 pt-3.5">
        <button
          type="button"
          onClick={onApproveAsIs}
          disabled={isSubmitting}
          className="rounded-[11px] bg-[#2563eb] px-[22px] py-3 text-sm font-extrabold text-white shadow-[0_2px_8px_rgba(37,99,235,0.28)] hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-50"
        >
          초안 그대로 승인
        </button>
        <button
          type="button"
          onClick={onApproveEdited}
          disabled={isSubmitting || !edited}
          className="rounded-[11px] border border-[#cbd5e1] bg-white px-5 py-3 text-sm font-bold text-[#334155] hover:bg-[#f8fafc] disabled:cursor-not-allowed disabled:opacity-40"
          title={edited ? undefined : "초안을 수정하면 활성화돼요"}
        >
          수정한 내용으로 승인
        </button>
        <span className="flex-1" />
        {toast && (
          <span className="animate-[fadeup_0.25s_ease_both] text-[13px] font-bold text-[#16a34a]">
            {toast}
          </span>
        )}
      </div>
    </div>
  );
}
