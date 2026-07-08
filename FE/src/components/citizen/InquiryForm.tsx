import { useState } from "react";
import { EXAMPLE_CHIPS } from "../../constants/options";

interface InquiryFormProps {
  onSubmit: (text: string) => void;
  onGoHistory: () => void;
}

export default function InquiryForm({ onSubmit, onGoHistory }: InquiryFormProps) {
  const [text, setText] = useState("");
  const canSubmit = text.trim().length > 0;

  return (
    <div className="animate-[fadeup_0.35s_ease_both]">
      <div className="mb-[22px] text-center">
        <h1 className="mb-2 text-2xl font-extrabold tracking-tight">
          무엇을 도와드릴까요?
        </h1>
        <p className="text-sm leading-relaxed text-[#64748b]">
          문의하실 내용을 자유롭게 작성해 주세요.
          <br />
          담당자가 확인 후 등록하신 연락처로 안내드립니다.
        </p>
      </div>

      <div className="rounded-2xl border border-[#e2e8f0] bg-white p-[18px] shadow-sm">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="예) 전기안전관리자 선임 안 하면 벌금 있나요?"
          className="min-h-[132px] w-full resize-y p-1 text-[15px] leading-relaxed text-[#0f172a] outline-none"
        />
        <div className="mt-1.5 border-t border-[#f1f5f9] pt-[13px]">
          <div className="mb-[9px] text-[11.5px] font-bold text-[#94a3b8]">
            이런 질문을 많이 하세요
          </div>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => setText(chip)}
                className="rounded-[9px] border border-[#e2e8f0] bg-[#f8fafc] px-3 py-[7px] text-left text-[12.5px] font-medium leading-tight text-[#334155] hover:bg-[#f1f5f9]"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        type="button"
        disabled={!canSubmit}
        onClick={() => onSubmit(text.trim())}
        className="mt-3.5 w-full rounded-[13px] bg-[#2563eb] py-[15px] text-[15px] font-bold text-white transition-opacity hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
      >
        문의 등록
      </button>

      <div className="mt-[18px] text-center">
        <button
          type="button"
          onClick={onGoHistory}
          className="text-[13px] font-semibold text-[#64748b] hover:text-[#334155]"
        >
          내 문의함 →
        </button>
      </div>
    </div>
  );
}
