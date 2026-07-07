interface LlmErrorBannerProps {
  error: string;
}

export default function LlmErrorBanner({ error }: LlmErrorBannerProps) {
  return (
    <div className="mb-[18px] flex items-start gap-[11px] rounded-[10px] border border-[#fecaca] border-l-4 border-l-[#dc2626] bg-[#fef2f2] px-4 py-3.5">
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#dc2626"
        strokeWidth="2.2"
        className="mt-px flex-none"
      >
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
        <circle cx="12" cy="12" r="9" />
      </svg>
      <div>
        <div className="mb-0.5 text-[13.5px] font-extrabold text-[#b91c1c]">
          AI 답변 생성 실패 — 근거 문서를 참고해 직접 작성해 주세요
        </div>
        <div className="font-mono text-[12px] text-[#dc2626]">{error}</div>
      </div>
    </div>
  );
}
