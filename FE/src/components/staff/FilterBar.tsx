interface FilterBarProps {
  options: readonly string[];
  active: string;
  onChange: (value: string) => void;
}

export default function FilterBar({ options, active, onChange }: FilterBarProps) {
  return (
    <div className="flex flex-wrap gap-[7px]">
      {options.map((opt) => {
        const isActive = active === opt;
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={[
              "rounded-lg border px-2.5 py-1 text-[12px] font-bold transition-colors",
              isActive
                ? "border-[#2563eb] bg-[#2563eb] text-white"
                : "border-[#e2e8f0] bg-white text-[#64748b] hover:bg-[#f8fafc]",
            ].join(" ")}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}
