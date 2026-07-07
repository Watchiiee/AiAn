import type { Ticket, TicketStatus } from "../../types/inquiry";
import {
  priorityBadgeClass,
  priorityDotClass,
  typeBadgeClass,
  statusBadgeClass,
} from "../../utils/badges";

interface InboxItemProps {
  ticket: Ticket;
  status: TicketStatus;
  selected: boolean;
  onSelect: () => void;
}

export default function InboxItem({
  ticket,
  status,
  selected,
  onSelect,
}: InboxItemProps) {
  return (
    <div
      onClick={onSelect}
      className={[
        "cursor-pointer rounded-xl border p-3 transition-colors",
        selected
          ? "border-[#2563eb] bg-[#eff6ff]"
          : "border-transparent hover:bg-[#f8fafc]",
      ].join(" ")}
    >
      <div className="mb-[7px] flex items-center gap-1.5">
        <span className={priorityBadgeClass(ticket.rule.priority)}>
          <span className={priorityDotClass(ticket.rule.priority)} />
          {ticket.rule.priority}
        </span>
        <span className={typeBadgeClass(ticket.classification.type)}>
          {ticket.classification.type}
        </span>
        <span className="flex-1" />
        <span className={statusBadgeClass(status)}>{status}</span>
      </div>

      <p className="mb-1.5 line-clamp-2 text-[13.5px] font-semibold leading-snug text-[#1e293b]">
        {ticket.original_text}
      </p>

      <div className="flex items-center gap-2 text-[11.5px] text-[#94a3b8]">
        <span className="font-semibold text-[#64748b]">
          {ticket.rule.department}
        </span>
        <span>·</span>
        <span>{ticket.ticket_id}</span>
      </div>
    </div>
  );
}
