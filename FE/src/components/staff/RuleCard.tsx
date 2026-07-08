import { useEffect, useState } from "react";
import type { Priority } from "../../types/inquiry";
import { PRIORITY_OPTIONS, DEPT_OPTIONS } from "../../constants/options";
import { priorityBadgeClass, priorityDotClass } from "../../utils/badges";

interface RuleCardProps {
  priority: Priority;
  department: string;
  /** master 계정일 때만 true. staff는 읽기 전용으로 본다. */
  editable: boolean;
  onSave?: (priority: Priority, department: string) => void;
  isSaving?: boolean;
}

const selectClass =
  "w-full cursor-pointer rounded-[9px] border border-[#cbd5e1] bg-white px-[11px] py-[9px] text-[13.5px] font-semibold text-[#1e293b] outline-none focus:border-[#2563eb]";
const labelClass = "mb-1.5 block text-[11.5px] font-semibold text-[#64748b]";

export default function RuleCard({
  priority,
  department,
  editable,
  onSave,
  isSaving = false,
}: RuleCardProps) {
  const [draftPriority, setDraftPriority] = useState(priority);
  const [draftDept, setDraftDept] = useState(department);

  // 다른 항목을 선택하거나 서버 값이 갱신되면 로컬 편집 상태를 동기화
  useEffect(() => {
    setDraftPriority(priority);
    setDraftDept(department);
  }, [priority, department]);

  const changed = draftPriority !== priority || draftDept !== department;

  if (!editable) {
    return (
      <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
        <div className="mb-3 text-[11.5px] font-bold text-[#94a3b8]">
          우선순위 · 담당부서
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={priorityBadgeClass(priority)}>
            <span className={priorityDotClass(priority)} />
            {priority}
          </span>
          <span className="rounded-md border border-[#e2e8f0] bg-[#f8fafc] px-2.5 py-1 text-[12.5px] font-bold text-[#334155]">
            {department}
          </span>
        </div>
        <p className="mt-3 text-[11.5px] text-[#94a3b8]">
          재배정은 최고관리자만 할 수 있어요.
        </p>
      </div>
    );
  }

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
        disabled={!changed || isSaving}
        onClick={() => onSave?.(draftPriority, draftDept)}
        className="w-full rounded-[9px] bg-[#2563eb] py-2.5 text-[13px] font-bold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
      >
        {isSaving ? "저장 중…" : "재배정 저장"}
      </button>
    </div>
  );
}
