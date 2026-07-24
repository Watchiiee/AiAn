import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { loginUser } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";
import { homePathForRole } from "../utils/roleRoute";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, expired, clearExpiredFlag } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };

  const mutation = useMutation({
    mutationFn: () => loginUser(email, password),
    onSuccess: (res) => {
      login({ token: res.access_token, role: res.role, email, department: res.department });
      const fallback = homePathForRole(res.role);
      navigate(location.state?.from ?? fallback, { replace: true });
    },
  });

  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "로그인에 실패했어요. 다시 시도해 주세요."
        : null;

  return (
    <main className="flex flex-1 items-center justify-center overflow-y-auto px-[18px] py-10">
      <div className="w-full max-w-[400px]">
        <div className="mb-7 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-[11px] bg-gradient-to-br from-[#2563eb] to-[#1d4ed8] text-base font-extrabold text-white">
            Ai
          </div>
          <h1 className="text-xl font-extrabold tracking-tight">AiAn 로그인</h1>
          <p className="mt-1 text-[13px] text-[#64748b]">
            협회 민원 대응 AI 시스템
          </p>
        </div>

        {expired && (
          <div className="mb-4 rounded-[10px] border border-[#fde68a] bg-[#fffbeb] px-3.5 py-3 text-[13px] font-semibold text-[#b45309]">
            세션이 만료되었어요. 다시 로그인해 주세요.
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            clearExpiredFlag();
            mutation.mutate();
          }}
          className="rounded-2xl border border-[#e2e8f0] bg-white p-6 shadow-sm"
        >
          <label className="mb-1.5 block text-[12.5px] font-semibold text-[#64748b]">
            이메일
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="mb-4 w-full rounded-[10px] border border-[#cbd5e1] px-3 py-2.5 text-[14px] outline-none focus:border-[#2563eb]"
          />

          <label className="mb-1.5 block text-[12.5px] font-semibold text-[#64748b]">
            비밀번호
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8자 이상"
            className="mb-2 w-full rounded-[10px] border border-[#cbd5e1] px-3 py-2.5 text-[14px] outline-none focus:border-[#2563eb]"
          />

          {errorMessage && (
            <p className="mb-3 text-[12.5px] font-semibold text-[#dc2626]">
              {errorMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={mutation.isPending}
            className="mt-2 w-full rounded-[11px] bg-[#2563eb] py-3 text-[14px] font-bold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? "로그인 중…" : "로그인"}
          </button>
        </form>

        <p className="mt-4 text-center text-[13px] text-[#64748b]">
          계정이 없으신가요?{" "}
          <Link to="/register" className="font-bold text-[#2563eb]">
            회원가입
          </Link>
        </p>
      </div>
    </main>
  );
}
