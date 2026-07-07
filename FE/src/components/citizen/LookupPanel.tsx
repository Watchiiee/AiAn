import { useState } from "react";
import type { TicketStatus } from "../../types/inquiry";
import { statusBadgeClass } from "../../utils/badges";

interface LookupPanelProps {
  onBack: () => void;
}

interface LookupResult {
  ticketNo: string;
  status: TicketStatus;
  department: string;
}

export default function LookupPanel({ onBack }: LookupPanelProps) {
  const [ticketNo, setTicketNo] = useState("");
  const [result, setResult] = useState<LookupResult | null>(null);

  // 데모용 조회. 실제로는 GET /api/inquiries/:ticketNo 로 교체.
  function handleLookup() {
    const id = ticketNo.trim();
    if (!id) return;
    setResult({
      ticketNo: id,
      status: "검토중",
      department: "민원안내팀",
    });
  }

  return (
    <div className="animate-[fadeup_0.35s_ease_both]">
      <div className="mb-4">
        <button
          type="button"
          onClick={onBack}
          className="text-[13px] font-semibold text-[#64748b] hover:text-[#334155]"
        >
          ← 문의하기로 돌아가기
        </button>
      </div>

      <div className="rounded-2xl border border-[#e2e8f0] bg-white p-[22px] shadow-sm">
        <h2 className="mb-1 text-lg font-extrabold">내 문의 조회</h2>
        <p className="mb-4 text-[12.5px] text-[#94a3b8]">
          접수번호를 입력하면 처리 상태를 확인할 수 있습니다.
        </p>

        <div className="flex gap-2">
          <input
            value={ticketNo}
            onChange={(e) => setTicketNo(e.target.value)}
            placeholder="예) AiAn-20260707-0042"
            className="flex-1 rounded-[10px] border border-[#cbd5e1] px-3 py-2.5 text-[13.5px] outline-none focus:border-[#2563eb]"
          />
          <button
            type="button"
            onClick={handleLookup}
            className="rounded-[10px] bg-[#2563eb] px-4 text-[13.5px] font-bold text-white hover:bg-[#1d4ed8]"
          >
            조회
          </button>
        </div>

        {result && (
          <div className="mt-4 rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-[18px]">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] font-semibold text-[#64748b]">
                {result.ticketNo}
              </span>
              <span className={statusBadgeClass(result.status)}>
                {result.status}
              </span>
            </div>
            <p className="mt-3 text-[13px] text-[#475569]">
              현재 <b>{result.department}</b>에서 검토 중입니다. 확인 후
              등록하신 연락처로 안내드립니다.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
