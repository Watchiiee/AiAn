import type { PendingInquiry } from "../../types/inquiry";
import {
  priorityBadgeClass,
  priorityDotClass,
  typeBadgeClass,
  deptChangeBadgeClass,
} from "../../utils/badges";
import { formatDateTime } from "../../utils/format";

interface InboxItemProps {
  inquiry: PendingInquiry;
  selected: boolean;
  onSelect: () => void;
}

export default function InboxItem({ inquiry, selected, onSelect }: InboxItemProps) {
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
      <div className="mb-[7px] flex flex-wrap items-center gap-1.5">
        <span className={priorityBadgeClass(inquiry.priority)}>
          <span className={priorityDotClass(inquiry.priority)} />
          {inquiry.priority}
        </span>
        <span className={typeBadgeClass(inquiry.inquiry_type)}>
          {inquiry.inquiry_type}
        </span>
        {inquiry.dept_change_requested && (
          <span className={deptChangeBadgeClass()}>부서변경 요청됨</span>
        )}
      </div>

      <p className="mb-1.5 line-clamp-2 text-[13.5px] font-semibold leading-snug text-[#1e293b]">
        {inquiry.original_text}
      </p>

      <div className="flex items-center gap-2 text-[11.5px] text-[#94a3b8]">
        <span className="font-semibold text-[#64748b]">{inquiry.department}</span>
        <span>·</span>
        <span>#{inquiry.id}</span>
        <span>·</span>
        <span>{formatDateTime(inquiry.created_at)}</span>
      </div>
    </div>
  );
}
