import { useMemo, useState } from "react";
import { useMyInquiries } from "../../hooks/useMyInquiries";
import { MY_STATUS_FILTERS } from "../../constants/options";
import MyInquiryItem from "./MyInquiryItem";
import Spinner from "../common/Spinner";

interface MyInquiriesProps {
  onBack: () => void;
}

function filterClass(active: boolean): string {
  return [
    "rounded-lg border px-2.5 py-1 text-[12px] font-bold transition-colors",
    active
      ? "border-[#2563eb] bg-[#2563eb] text-white"
      : "border-[#e2e8f0] bg-white text-[#64748b] hover:bg-[#f8fafc]",
  ].join(" ");
}

export default function MyInquiries({ onBack }: MyInquiriesProps) {
  const { data, isLoading, isError } = useMyInquiries();
  const [statusFilter, setStatusFilter] =
    useState<(typeof MY_STATUS_FILTERS)[number]>("전체");

  const filtered = useMemo(() => {
    const list = data ?? [];
    if (statusFilter === "답변 대기중") return list.filter((i) => i.status === "pending");
    if (statusFilter === "답변 완료") return list.filter((i) => i.status === "answered");
    return list;
  }, [data, statusFilter]);

  return (
    <div className="animate-[fadeup_0.35s_ease_both]">
      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="text-[13px] font-semibold text-[#64748b] hover:text-[#334155]"
        >
          ← 문의하기로 돌아가기
        </button>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-extrabold">내 문의함</h2>
        <div className="flex gap-[7px]">
          {MY_STATUS_FILTERS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setStatusFilter(opt)}
              className={filterClass(statusFilter === opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : isError ? (
        <p className="rounded-xl border border-[#fecaca] bg-[#fef2f2] p-4 text-center text-[13px] font-semibold text-[#dc2626]">
          문의 내역을 불러오지 못했어요.
        </p>
      ) : filtered.length === 0 ? (
        <p className="rounded-xl border border-[#e2e8f0] bg-white p-8 text-center text-[13px] text-[#94a3b8]">
          등록된 문의가 없습니다.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((inquiry) => (
            <MyInquiryItem key={inquiry.id} inquiry={inquiry} />
          ))}
        </div>
      )}
    </div>
  );
}
