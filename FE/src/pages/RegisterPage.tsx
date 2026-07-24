import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { registerUser } from "../api/auth";
import { ApiError } from "../api/client";

const MIN_PASSWORD_LENGTH = 8;

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const navigate = useNavigate();

  const mismatch =
    passwordConfirm.length > 0 && password !== passwordConfirm;
  const tooShort =
    password.length > 0 && password.length < MIN_PASSWORD_LENGTH;

  const mutation = useMutation({
    mutationFn: () => registerUser(email, password),
    onSuccess: () => {
      // 가입은 항상 일반 사용자로 생성된다. 로그인 화면으로 보내며 이메일을 넘겨준다.
      navigate("/login", { state: { from: undefined }, replace: true });
    },
  });

  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "회원가입에 실패했어요. 다시 시도해 주세요."
        : null;

  const canSubmit =
    email.length > 0 &&
    password.length >= MIN_PASSWORD_LENGTH &&
    password === passwordConfirm;

  return (
    <main className="flex flex-1 items-center justify-center overflow-y-auto px-[18px] py-10">
      <div className="w-full max-w-[400px]">
        <div className="mb-7 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-[11px] bg-gradient-to-br from-[#2563eb] to-[#1d4ed8] text-base font-extrabold text-white">
            Ai
          </div>
          <h1 className="text-xl font-extrabold tracking-tight">회원가입</h1>
          <p className="mt-1 text-[13px] text-[#64748b]">
            가입 후 민원 문의를 등록할 수 있어요.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) mutation.mutate();
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
            className="mb-1 w-full rounded-[10px] border border-[#cbd5e1] px-3 py-2.5 text-[14px] outline-none focus:border-[#2563eb]"
          />
          {tooShort && (
            <p className="mb-3 text-[12px] font-semibold text-[#d97706]">
              비밀번호는 8자 이상이어야 해요.
            </p>
          )}

          <label className="mb-1.5 mt-3 block text-[12.5px] font-semibold text-[#64748b]">
            비밀번호 확인
          </label>
          <input
            type="password"
            required
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            placeholder="비밀번호를 다시 입력하세요"
            className="mb-1 w-full rounded-[10px] border border-[#cbd5e1] px-3 py-2.5 text-[14px] outline-none focus:border-[#2563eb]"
          />
          {mismatch && (
            <p className="mb-3 text-[12px] font-semibold text-[#dc2626]">
              비밀번호가 일치하지 않아요.
            </p>
          )}

          {errorMessage && (
            <p className="mb-3 mt-2 text-[12.5px] font-semibold text-[#dc2626]">
              {errorMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={!canSubmit || mutation.isPending}
            className="mt-3 w-full rounded-[11px] bg-[#2563eb] py-3 text-[14px] font-bold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? "가입 처리 중…" : "회원가입"}
          </button>
        </form>

        <p className="mt-4 text-center text-[13px] text-[#64748b]">
          이미 계정이 있으신가요?{" "}
          <Link to="/login" className="font-bold text-[#2563eb]">
            로그인
          </Link>
        </p>
      </div>
    </main>
  );
}
