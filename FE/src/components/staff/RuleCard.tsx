import { useEffect, useState } from "react";
import type { PendingInquiry, Priority } from "../../types/inquiry";
import { PRIORITY_OPTIONS, DEPT_OPTIONS } from "../../constants/options";
import { priorityBadgeClass, priorityDotClass, deptChangeBadgeClass } from "../../utils/badges";

interface RuleCardProps {
  inquiry: PendingInquiry;
  /** master 면 재배정 가능, staff 면 "부서 변경 요청"만 가능 */
  canReassign: boolean;
  onSaveRule: (priority: Priority, department: string) => void;
  isSavingRule: boolean;
  onRequestDeptChange: (reason: string, suggestedDepartment: string | null) => void;
  isRequestingDeptChange: boolean;
}

const selectClass =
  "w-full cursor-pointer rounded-[9px] border border-[#cbd5e1] bg-white px-[11px] py-[9px] text-[13.5px] font-semibold text-[#1e293b] outline-none focus:border-[#2563eb]";
const labelClass = "mb-1.5 block text-[11.5px] font-semibold text-[#64748b]";

export default function RuleCard({
  inquiry,
  canReassign,
  onSaveRule,
  isSavingRule,
  onRequestDeptChange,
  isRequestingDeptChange,
}: RuleCardProps) {
  const { priority, department } = inquiry;

  const [draftPriority, setDraftPriority] = useState(priority);
  const [draftDept, setDraftDept] = useState(department);

  // 다른 항목을 선택하거나 서버 값이 갱신되면 로컬 편집 상태를 동기화
  useEffect(() => {
    setDraftPriority(priority);
    setDraftDept(department);
  }, [priority, department]);

  const changed = draftPriority !== priority || draftDept !== department;

  // master: 편집 가능한 재배정 UI
  if (canReassign) {
    return (
      <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
        <div className="mb-[11px] flex items-center justify-between">
          <span className="text-[11.5px] font-bold text-[#94a3b8]">
            우선순위 · 담당부서 <span className="font-medium text-[#cbd5e1]">· 재배정 가능</span>
          </span>
          <span className="rounded-md bg-[#eff6ff] px-2 py-0.5 text-[10.5px] font-bold text-[#2563eb]">
            최고관리자
          </span>
        </div>

        {inquiry.dept_change_requested && (
          <div className="mb-3 rounded-[10px] border border-[#ddd6fe] bg-[#f5f3ff] px-3.5 py-3">
            <div className="mb-1 flex items-center gap-1.5">
              <span className={deptChangeBadgeClass()}>부서변경 요청됨</span>
              {inquiry.dept_change_requested_by && (
                <span className="text-[11px] font-semibold text-[#7c3aed]">
                  {inquiry.dept_change_requested_by}
                </span>
              )}
            </div>
            {inquiry.dept_change_reason && (
              <p className="text-[12.5px] leading-relaxed text-[#5b21b6]">
                {inquiry.dept_change_reason}
              </p>
            )}
            {inquiry.dept_change_suggested && (
              <p className="mt-1 text-[12px] font-bold text-[#6d28d9]">
                제안 부서: {inquiry.dept_change_suggested}
              </p>
            )}
          </div>
        )}

        <label className={labelClass}>우선순위</label>
        <select
          value={draftPriority}
          onChange={(e) => setDraftPriority(e.target.value as Priority)}
          className={`${selectClass} mb-[13px]`}
        >
          {PRIORITY_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>

        <label className={labelClass}>담당부서</label>
        <select
          value={draftDept}
          onChange={(e) => setDraftDept(e.target.value)}
          className={`${selectClass} mb-[13px]`}
        >
          {DEPT_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>

        <button
          type="button"
          disabled={!changed || isSavingRule}
          onClick={() => onSaveRule(draftPriority, draftDept)}
          className="w-full rounded-[9px] bg-[#2563eb] py-2.5 text-[13px] font-bold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isSavingRule ? "저장 중…" : "재배정 저장"}
        </button>
      </div>
    );
  }

  // staff: 읽기 전용 + 이미 요청했으면 요청 내용 표시, 아니면 요청 폼
  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
      <div className="mb-3 text-[11.5px] font-bold text-[#94a3b8]">
        우선순위 · 담당부서
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className={priorityBadgeClass(priority)}>
          <span className={priorityDotClass(priority)} />
          {priority}
        </span>
        <span className="rounded-md border border-[#e2e8f0] bg-[#f8fafc] px-2.5 py-1 text-[12.5px] font-bold text-[#334155]">
          {department}
        </span>
      </div>

      {inquiry.dept_change_requested ? (
        <div className="rounded-[10px] border border-[#ddd6fe] bg-[#f5f3ff] px-3.5 py-3">
          <span className={deptChangeBadgeClass()}>부서변경 요청됨</span>
          {inquiry.dept_change_reason && (
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-[#5b21b6]">
              {inquiry.dept_change_reason}
            </p>
          )}
          {inquiry.dept_change_suggested && (
            <p className="mt-1 text-[12px] font-bold text-[#6d28d9]">
              제안 부서: {inquiry.dept_change_suggested}
            </p>
          )}
          <p className="mt-1.5 text-[11px] text-[#8b7fc9]">
            최고관리자 확인을 기다리고 있어요.
          </p>
        </div>
      ) : (
        <DeptChangeRequestForm
          onSubmit={onRequestDeptChange}
          isSubmitting={isRequestingDeptChange}
        />
      )}
    </div>
  );
}

function DeptChangeRequestForm({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (reason: string, suggestedDepartment: string | null) => void;
  isSubmitting: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [suggested, setSuggested] = useState("");

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full rounded-[9px] border border-[#e2e8f0] bg-[#f8fafc] py-2.5 text-[12.5px] font-bold text-[#64748b] hover:bg-[#f1f5f9]"
      >
        이 부서가 아닌 것 같아요 · 변경 요청
      </button>
    );
  }

  return (
    <div>
      <label className={labelClass}>요청 이유</label>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="예) 이건 우리 부서 업무가 아닌 것 같습니다"
        className="mb-[9px] min-h-[64px] w-full resize-y rounded-[9px] border border-[#cbd5e1] p-2.5 text-[13px] outline-none focus:border-[#2563eb]"
      />

      <label className={labelClass}>제안 부서 (선택)</label>
      <select
        value={suggested}
        onChange={(e) => setSuggested(e.target.value)}
        className={`${selectClass} mb-[11px]`}
      >
        <option value="">제안 부서 없음</option>
        {DEPT_OPTIONS.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>

      <div className="flex gap-2">
        <button
          type="button"
          disabled={!reason.trim() || isSubmitting}
          onClick={() => {
            onSubmit(reason.trim(), suggested || null);
            setOpen(false);
            setReason("");
            setSuggested("");
          }}
          className="flex-1 rounded-[9px] bg-[#2563eb] py-2.5 text-[13px] font-bold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isSubmitting ? "요청 중…" : "요청 보내기"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-[9px] border border-[#cbd5e1] px-4 text-[13px] font-bold text-[#64748b] hover:bg-[#f8fafc]"
        >
          취소
        </button>
      </div>
    </div>
  );
}
