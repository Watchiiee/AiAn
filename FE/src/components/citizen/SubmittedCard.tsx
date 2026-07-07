interface SubmittedCardProps {
  ticketNo: string;
  onNewInquiry: () => void;
  onGoLookup: () => void;
}

export default function SubmittedCard({
  ticketNo,
  onNewInquiry,
  onGoLookup,
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
          담당자 확인 후 등록하신 연락처로 안내드립니다.
        </p>

        <div className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-[18px] text-left">
          <div className="flex items-center justify-between border-b border-[#e2e8f0] pb-[13px]">
            <span className="text-[12.5px] font-semibold text-[#64748b]">
              접수번호
            </span>
            <span className="text-sm font-extrabold tracking-wide text-[#2563eb]">
              {ticketNo}
            </span>
          </div>
          <div className="flex justify-between pt-3">
            <span className="text-[12.5px] font-semibold text-[#64748b]">
              예상 담당부서
            </span>
            <span className="text-[13px] font-bold">민원안내팀</span>
          </div>
          <div className="flex justify-between pt-[9px]">
            <span className="text-[12.5px] font-semibold text-[#64748b]">
              예상 처리시간
            </span>
            <span className="text-[13px] font-bold">영업일 기준 1~2일</span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={onNewInquiry}
        className="mt-3.5 w-full rounded-[13px] bg-[#2563eb] py-[15px] text-[15px] font-bold text-white hover:bg-[#1d4ed8]"
      >
        새 문의 등록
      </button>

      <div className="mt-4 text-center">
        <button
          type="button"
          onClick={onGoLookup}
          className="text-[13px] font-semibold text-[#64748b] hover:text-[#334155]"
        >
          내 문의 조회 →
        </button>
      </div>
    </div>
  );
}
