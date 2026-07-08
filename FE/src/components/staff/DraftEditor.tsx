import type { AnswerConfidence } from "../../types/inquiry";
import { answerConfidenceBadgeClass, answerConfidenceLabel } from "../../utils/badges";

interface DraftEditorProps {
  value: string;
  answerConfidence: AnswerConfidence;
  onChange: (value: string) => void;
}

export default function DraftEditor({
  value,
  answerConfidence,
  onChange,
}: DraftEditorProps) {
  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
      <div className="mb-[11px] flex flex-wrap items-center justify-between gap-2">
        <span className="text-[13.5px] font-extrabold text-[#1e293b]">
          답변 초안
        </span>
        <div className="flex items-center gap-1.5">
          <span className={answerConfidenceBadgeClass(answerConfidence)}>
            {answerConfidenceLabel(answerConfidence)}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md border border-[#bfdbfe] bg-[#eff6ff] px-2.5 py-1 text-[11px] font-extrabold text-[#2563eb]">
            ✎ AI 초안 · 검토 필요
          </span>
        </div>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="AI 답변이 생성되지 않았습니다. 아래 근거 문서를 참고해 직접 작성해 주세요."
        className="min-h-[150px] w-full resize-y rounded-[10px] border border-[#e2e8f0] bg-[#fbfcfe] p-3.5 text-sm leading-relaxed text-[#1e293b] outline-none focus:border-[#2563eb]"
      />
    </div>
  );
}
