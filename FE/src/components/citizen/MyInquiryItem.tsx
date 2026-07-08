import { useState } from "react";
import type { MyInquiry } from "../../types/inquiry";
import { recordStatusBadgeClass, recordStatusLabel } from "../../utils/badges";
import { formatDateTime } from "../../utils/format";

interface MyInquiryItemProps {
  inquiry: MyInquiry;
}

export default function MyInquiryItem({ inquiry }: MyInquiryItemProps) {
  const [open, setOpen] = useState(false);
  const answered = inquiry.status === "answered";

  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full flex-col gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          <span className={recordStatusBadgeClass(inquiry.status)}>
            {recordStatusLabel(inquiry.status)}
          </span>
          <span className="text-[11.5px] font-semibold text-[#94a3b8]">
            #{inquiry.id} · {formatDateTime(inquiry.created_at)}
          </span>
        </div>
        <p className="text-[14px] font-semibold leading-relaxed text-[#1e293b]">
          {inquiry.original_text}
        </p>
        <div className="text-[12px] font-semibold text-[#64748b]">
          담당부서: {inquiry.department}
        </div>
      </button>

      {open && (
        <div className="mt-3 border-t border-[#f1f5f9] pt-3">
          {answered ? (
            <div className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-3.5">
              <div className="mb-1.5 text-[11.5px] font-bold text-[#94a3b8]">
                답변
              </div>
              <p className="whitespace-pre-line text-[13.5px] leading-relaxed text-[#1e293b]">
                {inquiry.answer}
              </p>
            </div>
          ) : (
            <p className="rounded-xl border border-[#fde68a] bg-[#fffbeb] p-3.5 text-[13px] font-semibold text-[#b45309]">
              담당자가 검토 중입니다. 확인되는 대로 이곳에서 답변을 볼 수 있어요.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
