import { useMemo } from "react";
import type { PendingInquiry } from "../../types/inquiry";
import FilterBar from "./FilterBar";
import InboxItem from "./InboxItem";
import { PRIORITY_FILTERS } from "../../constants/options";

interface InboxProps {
  inquiries: PendingInquiry[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  priorityFilter: string;
  onPriorityFilter: (v: string) => void;
}

export default function Inbox({
  inquiries,
  selectedId,
  onSelect,
  priorityFilter,
  onPriorityFilter,
}: InboxProps) {
  // v4 델타: 서버가 이제 긴급 우선 + created_at 오래된순으로 정렬해서 준다.
  // 여기서 다시 정렬하면 서버 정렬을 덮어쓰게 되므로, 필터링만 하고 순서는 그대로 둔다.
  const filtered = useMemo(() => {
    if (priorityFilter === "전체") return inquiries;
    return inquiries.filter((t) => t.priority === priorityFilter);
  }, [inquiries, priorityFilter]);

  return (
    <aside className="aian-scroll flex w-[390px] flex-none flex-col overflow-y-auto border-r border-[#e2e8f0] bg-white">
      <div className="sticky top-0 z-[5] border-b border-[#f1f5f9] bg-white px-[18px] pb-3 pt-4">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-[16px] font-extrabold">검토 대기 목록</h2>
          <span className="text-[12px] font-semibold text-[#94a3b8]">
            {filtered.length}건
          </span>
        </div>
        <FilterBar
          options={PRIORITY_FILTERS}
          active={priorityFilter}
          onChange={onPriorityFilter}
        />
      </div>

      <div className="px-3 pb-5 pt-2.5">
        {filtered.length === 0 ? (
          <p className="px-2 py-10 text-center text-[13px] text-[#94a3b8]">
            검토 대기 중인 민원이 없습니다.
          </p>
        ) : (
          filtered.map((t) => (
            <InboxItem
              key={t.id}
              inquiry={t}
              selected={selectedId === t.id}
              onSelect={() => onSelect(t.id)}
            />
          ))
        )}
      </div>
    </aside>
  );
}
