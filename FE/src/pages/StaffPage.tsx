import { useState, useRef, useCallback } from "react";
import type { Ticket, Priority, TicketStatus } from "../types/inquiry";
import Inbox from "../components/staff/Inbox";
import TicketDetail from "../components/staff/TicketDetail";
import Spinner from "../components/common/Spinner";
import { useTickets } from "../hooks/useTickets";

// 담당자가 수정한 값(초안·부서·우선순위·상태)을 티켓 id 별로 덮어쓰는 맵.
type Overrides<T> = Record<string, T>;

export default function StaffPage() {
  const { data: tickets, isLoading, isError } = useTickets();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState("전체");
  const [statusFilter, setStatusFilter] = useState("전체");

  const [statuses, setStatuses] = useState<Overrides<TicketStatus>>({});
  const [drafts, setDrafts] = useState<Overrides<string>>({});
  const [depts, setDepts] = useState<Overrides<string>>({});
  const [priorities, setPriorities] = useState<Overrides<Priority>>({});
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>();

  const statusOf = useCallback(
    (t: Ticket): TicketStatus => statuses[t.ticket_id] ?? t.status,
    [statuses],
  );

  function showToast(message: string) {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2200);
  }

  if (isLoading) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <Spinner />
      </main>
    );
  }
  if (isError || !tickets) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-[14px] text-[#dc2626]">
          민원 목록을 불러오지 못했어요.
        </p>
      </main>
    );
  }

  // 최초 진입 시 첫 티켓 자동 선택
  const effectiveSelectedId = selectedId ?? tickets[0]?.ticket_id ?? null;
  const selected = tickets.find((t) => t.ticket_id === effectiveSelectedId);

  return (
    <main className="flex min-h-0 flex-1">
      <Inbox
        tickets={tickets}
        statusOf={statusOf}
        selectedId={effectiveSelectedId}
        onSelect={setSelectedId}
        priorityFilter={priorityFilter}
        statusFilter={statusFilter}
        onPriorityFilter={setPriorityFilter}
        onStatusFilter={setStatusFilter}
      />

      <section className="aian-scroll min-w-0 flex-1 overflow-y-auto bg-[#eef2f7]">
        {selected ? (
          <TicketDetail
            ticket={selected}
            status={statusOf(selected)}
            draft={drafts[selected.ticket_id] ?? selected.answer_draft ?? ""}
            priority={priorities[selected.ticket_id] ?? selected.rule.priority}
            department={depts[selected.ticket_id] ?? selected.rule.department}
            toast={toast}
            onDraftChange={(v) =>
              setDrafts((prev) => ({ ...prev, [selected.ticket_id]: v }))
            }
            onPriorityChange={(p) =>
              setPriorities((prev) => ({ ...prev, [selected.ticket_id]: p }))
            }
            onDepartmentChange={(d) =>
              setDepts((prev) => ({ ...prev, [selected.ticket_id]: d }))
            }
            onSend={() => {
              setStatuses((prev) => ({
                ...prev,
                [selected.ticket_id]: "발송완료",
              }));
              showToast("답변이 발송되었습니다");
            }}
            onReassign={() => {
              setStatuses((prev) => ({
                ...prev,
                [selected.ticket_id]: "검토중",
              }));
              showToast("부서가 재배정되었습니다");
            }}
            onSaveDraft={() => showToast("임시 저장되었습니다")}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-[14px] text-[#94a3b8]">
              왼쪽에서 민원을 선택하세요.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
