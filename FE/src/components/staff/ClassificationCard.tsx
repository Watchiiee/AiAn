import type { Classification } from "../../types/inquiry";
import { typeBadgeClass } from "../../utils/badges";
import {
  isLowConfidence,
  confidencePercent,
  confidenceColor,
} from "../../utils/format";

interface ClassificationCardProps {
  classification: Classification;
}

export default function ClassificationCard({
  classification,
}: ClassificationCardProps) {
  const { type, key_request, confidence } = classification;
  const pct = confidencePercent(confidence);
  const color = confidenceColor(confidence);
  const lowConf = isLowConfidence(confidence);

  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
      <div className="mb-[11px] text-[11.5px] font-bold text-[#94a3b8]">
        AI 분류 결과
      </div>

      <div className="mb-3 flex items-center gap-2">
        <span className={typeBadgeClass(type, "lg")}>{type}</span>
        <span className="rounded-md bg-[#f8fafc] px-2 py-0.5 text-[10.5px] font-bold text-[#94a3b8]">
          {classification.domain === "technical" ? "기술질의" : "행정문의"}
        </span>
        {lowConf && (
          <span className="inline-flex items-center gap-1 rounded-md border border-[#fecaca] bg-[#fef2f2] px-2.5 py-1 text-[11px] font-extrabold text-[#dc2626]">
            ⚠ 분류 불확실
          </span>
        )}
      </div>

      <p className="mb-3.5 text-[13.5px] leading-relaxed text-[#475569]">
        {key_request}
      </p>

      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[11.5px] font-semibold text-[#64748b]">확신도</span>
        <span className="text-[12.5px] font-extrabold" style={{ color }}>
          {pct}%
        </span>
      </div>
      <div className="h-[7px] overflow-hidden rounded bg-[#f1f5f9]">
        <div
          className="h-full rounded"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}
