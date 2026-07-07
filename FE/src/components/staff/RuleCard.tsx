import type { Priority } from "../../types/inquiry";
import { PRIORITY_OPTIONS, DEPT_OPTIONS } from "../../constants/options";

interface RuleCardProps {
  priority: Priority;
  department: string;
  onPriorityChange: (p: Priority) => void;
  onDepartmentChange: (d: string) => void;
}

const selectClass =
  "w-full cursor-pointer rounded-[9px] border border-[#cbd5e1] bg-white px-[11px] py-[9px] text-[13.5px] font-semibold text-[#1e293b] outline-none focus:border-[#2563eb]";
const labelClass = "mb-1.5 block text-[11.5px] font-semibold text-[#64748b]";

export default function RuleCard({
  priority,
  department,
  onPriorityChange,
  onDepartmentChange,
}: RuleCardProps) {
  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
      <div className="mb-[11px] text-[11.5px] font-bold text-[#94a3b8]">
        AI 추천 룰 <span className="font-medium text-[#cbd5e1]">· 재배정 가능</span>
      </div>

      <label className={labelClass}>우선순위</label>
      <select
        value={priority}
        onChange={(e) => onPriorityChange(e.target.value as Priority)}
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
        value={department}
        onChange={(e) => onDepartmentChange(e.target.value)}
        className={selectClass}
      >
        {DEPT_OPTIONS.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}
