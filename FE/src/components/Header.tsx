import { NavLink } from "react-router-dom";

function tabClass(active: boolean): string {
  return [
    "rounded-[9px] px-3.5 py-1.5 text-[13px] font-bold transition-colors",
    active ? "bg-white text-[#2563eb] shadow-sm" : "text-[#64748b] hover:text-[#334155]",
  ].join(" ");
}

export default function Header() {
  return (
    <header className="sticky top-0 z-20 flex h-[60px] flex-none items-center justify-between border-b border-[#e2e8f0] bg-white px-[22px]">
      <div className="flex items-center gap-[11px]">
        <div className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-gradient-to-br from-[#2563eb] to-[#1d4ed8] text-[15px] font-extrabold tracking-tight text-white">
          Ai
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[16px] font-extrabold tracking-tight">AiAn</span>
          <span className="text-[11px] font-medium text-[#94a3b8]">
            협회 민원 대응 AI
          </span>
        </div>
      </div>

      <nav className="inline-flex gap-1 rounded-[11px] bg-[#f1f5f9] p-1">
        <NavLink to="/" end className={({ isActive }) => tabClass(isActive)}>
          민원인
        </NavLink>
        <NavLink to="/admin" className={({ isActive }) => tabClass(isActive)}>
          담당자
        </NavLink>
      </nav>
    </header>
  );
}
