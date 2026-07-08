import type { PendingInquiry } from "../../types/inquiry";
import { priorityBadgeClass, priorityDotClass, typeBadgeClass } from "../../utils/badges";
import { formatDateTime } from "../../utils/format";
import DraftEditor from "./DraftEditor";

interface TicketDetailProps {
  inquiry: PendingInquiry;
  draft: string;
  onDraftChange: (v: string) => void;
  onApproveAsIs: () => void;
  onApproveEdited: () => void;
  isSubmitting: boolean;
  toast: string | null;
}

export default function TicketDetail({
  inquiry,
  draft,
  onDraftChange,
  onApproveAsIs,
  onApproveEdited,
  isSubmitting,
  toast,
}: TicketDetailProps) {
  const edited = draft.trim() !== inquiry.answer_draft.trim();

  return (
    <div className="mx-auto max-w-[820px] px-[30px] pb-10 pt-[26px]">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="font-mono text-[12.5px] font-semibold text-[#94a3b8]">
          #{inquiry.id}
        </span>
        <span className={priorityBadgeClass(inquiry.priority)}>
          <span className={priorityDotClass(inquiry.priority)} />
          {inquiry.priority}
        </span>
        <span className={typeBadgeClass(inquiry.inquiry_type)}>
          {inquiry.inquiry_type}
        </span>
        <span className="text-[12px] font-semibold text-[#94a3b8]">
          {inquiry.department} · {formatDateTime(inquiry.created_at)}
        </span>
      </div>

      <div className="mb-4 rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
        <div className="mb-[9px] text-[11.5px] font-bold text-[#94a3b8]">
          민원 원문
        </div>
        <p className="text-[15px] leading-relaxed text-[#1e293b]">
          {inquiry.original_text}
        </p>
      </div>

      <div className="mb-4">
        <DraftEditor
          value={draft}
          answerConfidence={inquiry.answer_confidence}
          onChange={onDraftChange}
        />
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
