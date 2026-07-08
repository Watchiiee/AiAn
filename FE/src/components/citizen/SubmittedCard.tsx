interface SubmittedCardProps {
  inquiryId: number;
  onNewInquiry: () => void;
  onGoHistory: () => void;
}

export default function SubmittedCard({
  inquiryId,
  onNewInquiry,
  onGoHistory,
}: SubmittedCardProps) {
  return (
    <div className="animate-[fadeup_0.4s_ease_both]">
      <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[26px] py-[34px] text-center shadow-sm">
        <div className="mx-auto mb-[18px] flex h-[60px] w-[60px] animate-[pop_0.45s_ease_both] items-center justify-center rounded-full bg-[#dcfce7]">
          <svg
            width="30"
            height="30"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#16a34a"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </div>
        <h2 className="mb-2 text-xl font-extrabold tracking-tight">
          문의가 정상적으로 접수되었습니다
        </h2>
        <p className="mb-[22px] text-[13.5px] leading-relaxed text-[#64748b]">
          담당자 검토 후 답변이 확정되면 내 문의함에서 확인하실 수 있습니다.
        </p>

        <div className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-[18px] text-left">
          <div className="flex items-center justify-between">
            <span className="text-[12.5px] font-semibold text-[#64748b]">
              문의 번호
            </span>
            <span className="text-sm font-extrabold tracking-wide text-[#2563eb]">
              #{inquiryId}
            </span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={onGoHistory}
        className="mt-3.5 w-full rounded-[13px] bg-[#2563eb] py-[15px] text-[15px] font-bold text-white hover:bg-[#1d4ed8]"
      >
        내 문의함 보기
      </button>

      <div className="mt-4 text-center">
        <button
          type="button"
          onClick={onNewInquiry}
          className="text-[13px] font-semibold text-[#64748b] hover:text-[#334155]"
        >
          새 문의 등록하기
        </button>
      </div>
    </div>
  );
}
