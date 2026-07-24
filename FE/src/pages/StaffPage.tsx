import { useEffect, useRef, useState } from "react";
import Inbox from "../components/staff/Inbox";
import TicketDetail from "../components/staff/TicketDetail";
import CopilotPanel from "../components/staff/CopilotPanel";
import Spinner from "../components/common/Spinner";
import { usePendingInquiries } from "../hooks/usePendingInquiries";
import { useReviewInquiry } from "../hooks/useReviewInquiry";
import { useUpdateRule } from "../hooks/useUpdateRule";
import { useRequestDeptChange } from "../hooks/useRequestDeptChange";
import { useAuth } from "../context/AuthContext";
import type { Priority } from "../types/inquiry";

export default function StaffPage() {
  const { role } = useAuth();
  const canReassign = role === "master";

  const { data: inquiries, isLoading, isError } = usePendingInquiries();
  const review = useReviewInquiry();
  const updateRule = useUpdateRule();
  const requestDeptChange = useRequestDeptChange();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [priorityFilter, setPriorityFilter] = useState("전체");
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [toast, setToast] = useState<string | null>(null);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  function showToast(message: string) {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2200);
  }

  const list = inquiries ?? [];
  const effectiveSelectedId = selectedId ?? list[0]?.id ?? null;
  const selected = list.find((t) => t.id === effectiveSelectedId) ?? null;

  // 승인되면 목록에서 사라지므로, 선택된 항목이 없어지면 선택을 초기화한다.
  useEffect(() => {
    if (selectedId !== null && !list.some((t) => t.id === selectedId)) {
      setSelectedId(null);
    }
  }, [list, selectedId]);

  function handleApprove(id: number, finalAnswer: string | null) {
    review.mutate(
      { id, finalAnswer },
      {
        onSuccess: () => {
          showToast(
            finalAnswer === null
              ? "AI 초안 그대로 승인했습니다"
              : "수정한 내용으로 승인했습니다",
          );
        },
        onError: () => showToast("승인에 실패했어요. 다시 시도해 주세요."),
      },
    );
  }

  function handleSaveRule(id: number, priority: Priority, department: string) {
    updateRule.mutate(
      { id, priority, department },
      {
        onSuccess: () => showToast("부서/우선순위를 재배정했습니다"),
        onError: () => showToast("재배정에 실패했어요. 다시 시도해 주세요."),
      },
    );
  }

  function handleRequestDeptChange(
    id: number,
    reason: string,
    suggestedDepartment: string | null,
  ) {
    requestDeptChange.mutate(
      { id, reason, suggestedDepartment },
      {
        onSuccess: () => showToast("부서 변경을 요청했습니다"),
        onError: () => showToast("요청에 실패했어요. 다시 시도해 주세요."),
      },
    );
  }

  if (isLoading) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <Spinner />
      </main>
    );
  }
  if (isError) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-[14px] text-[#dc2626]">
          검토 대기 목록을 불러오지 못했어요.
        </p>
      </main>
    );
  }

  return (
    <main className="flex min-h-0 flex-1">
      <Inbox
        inquiries={list}
        selectedId={effectiveSelectedId}
        onSelect={setSelectedId}
        priorityFilter={priorityFilter}
        onPriorityFilter={setPriorityFilter}
      />

      <section className="aian-scroll min-w-0 flex-1 overflow-y-auto bg-[#eef2f7]">
        {selected ? (
          <TicketDetail
            inquiry={selected}
            draft={drafts[selected.id] ?? selected.answer_draft}
            onDraftChange={(v) =>
              setDrafts((prev) => ({ ...prev, [selected.id]: v }))
            }
            onApproveAsIs={() => handleApprove(selected.id, null)}
            onApproveEdited={() =>
              handleApprove(selected.id, drafts[selected.id] ?? selected.answer_draft)
            }
            isSubmitting={review.isPending}
            toast={toast}
            canReassign={canReassign}
            onSaveRule={(p, d) => handleSaveRule(selected.id, p, d)}
            isSavingRule={updateRule.isPending}
            onRequestDeptChange={(reason, suggested) =>
              handleRequestDeptChange(selected.id, reason, suggested)
            }
            isRequestingDeptChange={requestDeptChange.isPending}
            copilotOpen={copilotOpen}
            onToggleCopilot={() => setCopilotOpen((v) => !v)}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-[14px] text-[#94a3b8]">
              검토할 민원이 없습니다.
            </p>
          </div>
        )}
      </section>

      {selected && copilotOpen && (
        <CopilotPanel inquiryId={selected.id} onClose={() => setCopilotOpen(false)} />
      )}
    </main>
  );
}
