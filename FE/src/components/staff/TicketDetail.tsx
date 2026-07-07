import type { Ticket, Priority, TicketStatus } from "../../types/inquiry";
import { statusBadgeClass } from "../../utils/badges";
import LlmErrorBanner from "./LlmErrorBanner";
import ClassificationCard from "./ClassificationCard";
import RuleCard from "./RuleCard";
import DraftEditor from "./DraftEditor";
import EvidenceList from "./EvidenceList";

interface TicketDetailProps {
  ticket: Ticket;
  status: TicketStatus;
  draft: string;
  priority: Priority;
  department: string;
  toast: string | null;
  onDraftChange: (v: string) => void;
  onPriorityChange: (p: Priority) => void;
  onDepartmentChange: (d: string) => void;
  onSend: () => void;
  onReassign: () => void;
  onSaveDraft: () => void;
}

const secondaryBtn =
  "rounded-[11px] border border-[#cbd5e1] bg-white px-5 py-3 text-sm font-bold text-[#334155] hover:bg-[#f8fafc]";

export default function TicketDetail({
  ticket,
  status,
  draft,
  priority,
  department,
  toast,
  onDraftChange,
  onPriorityChange,
  onDepartmentChange,
  onSend,
  onReassign,
  onSaveDraft,
}: TicketDetailProps) {
  return (
    <div className="mx-auto max-w-[820px] px-[30px] pb-10 pt-[26px]">
      {ticket.llm_error && <LlmErrorBanner error={ticket.llm_error} />}

      <div className="mb-1.5 flex items-center gap-2.5">
        <span className="font-mono text-[12.5px] font-semibold text-[#94a3b8]">
          {ticket.ticket_id}
        </span>
        <span className={statusBadgeClass(status)}>{status}</span>
      </div>

      <div className="mb-4 rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
        <div className="mb-[9px] text-[11.5px] font-bold text-[#94a3b8]">
          민원 원문
        </div>
        <p className="text-[15px] leading-relaxed text-[#1e293b]">
          {ticket.original_text}
        </p>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <ClassificationCard classification={ticket.classification} />
        <RuleCard
          priority={priority}
          department={department}
          onPriorityChange={onPriorityChange}
          onDepartmentChange={onDepartmentChange}
        />
      </div>

      <div className="mb-4">
        <DraftEditor value={draft} onChange={onDraftChange} />
      </div>

      <div className="mb-4">
        <EvidenceList retrieved={ticket.retrieved} />
      </div>

      <div className="sticky bottom-0 flex items-center gap-2.5 bg-gradient-to-t from-[#eef2f7] from-70% to-transparent pb-1 pt-3.5">
        <button
          type="button"
          onClick={onSend}
          className="rounded-[11px] bg-[#2563eb] px-[26px] py-3 text-sm font-extrabold text-white shadow-[0_2px_8px_rgba(37,99,235,0.28)] hover:bg-[#1d4ed8]"
        >
          답변 발송
        </button>
        <button type="button" onClick={onReassign} className={secondaryBtn}>
          부서 재배정
        </button>
        <button type="button" onClick={onSaveDraft} className={secondaryBtn}>
          임시 저장
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
