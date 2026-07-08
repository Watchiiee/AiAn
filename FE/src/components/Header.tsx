import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Header() {
  const { isAuthenticated, session, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

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

      {isAuthenticated && session && (
        <div className="flex items-center gap-3">
          <div className="text-right leading-tight">
            <div className="text-[13px] font-bold text-[#1e293b]">
              {session.email}
            </div>
            <div className="text-[11px] font-semibold text-[#94a3b8]">
              {session.role === "staff" ? "담당자" : "일반 사용자"}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-[9px] border border-[#e2e8f0] px-3 py-1.5 text-[12.5px] font-bold text-[#64748b] hover:bg-[#f8fafc]"
          >
            로그아웃
          </button>
        </div>
      )}
    </header>
  );
}
