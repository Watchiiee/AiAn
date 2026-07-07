import { useMemo } from "react";
import type { Ticket, TicketStatus } from "../../types/inquiry";
import FilterBar from "./FilterBar";
import InboxItem from "./InboxItem";
import { PRIORITY_FILTERS, STATUS_FILTERS } from "../../constants/options";
import { sortByPriority } from "../../utils/format";

interface InboxProps {
  tickets: Ticket[];
  statusOf: (t: Ticket) => TicketStatus;
  selectedId: string | null;
  onSelect: (id: string) => void;
  priorityFilter: string;
  statusFilter: string;
  onPriorityFilter: (v: string) => void;
  onStatusFilter: (v: string) => void;
}

export default function Inbox({
  tickets,
  statusOf,
  selectedId,
  onSelect,
  priorityFilter,
  statusFilter,
  onPriorityFilter,
  onStatusFilter,
}: InboxProps) {
  const filtered = useMemo(() => {
    let list = tickets;
    if (priorityFilter !== "전체") {
      list = list.filter((t) => t.rule.priority === priorityFilter);
    }
    if (statusFilter !== "전체") {
      list = list.filter((t) => statusOf(t) === statusFilter);
    }
    return sortByPriority(list);
  }, [tickets, priorityFilter, statusFilter, statusOf]);

  return (
    <aside className="aian-scroll flex w-[390px] flex-none flex-col overflow-y-auto border-r border-[#e2e8f0] bg-white">
      <div className="sticky top-0 z-[5] border-b border-[#f1f5f9] bg-white px-[18px] pb-3 pt-4">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-[16px] font-extrabold">민원 인박스</h2>
          <span className="text-[12px] font-semibold text-[#94a3b8]">
            {filtered.length}건
          </span>
        </div>
        <FilterBar
          options={PRIORITY_FILTERS}
          active={priorityFilter}
          onChange={onPriorityFilter}
        />
        <div className="mt-[7px]">
          <FilterBar
            options={STATUS_FILTERS}
            active={statusFilter}
            onChange={onStatusFilter}
          />
        </div>
      </div>

      <div className="px-3 pb-5 pt-2.5">
        {filtered.length === 0 ? (
          <p className="px-2 py-10 text-center text-[13px] text-[#94a3b8]">
            조건에 맞는 민원이 없습니다.
          </p>
        ) : (
          filtered.map((t) => (
            <InboxItem
              key={t.ticket_id}
              ticket={t}
              status={statusOf(t)}
              selected={selectedId === t.ticket_id}
              onSelect={() => onSelect(t.ticket_id)}
            />
          ))
        )}
      </div>
    </aside>
  );
}
