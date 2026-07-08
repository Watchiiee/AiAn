import type { RetrievedDoc } from "../../types/inquiry";
import { scoreBadgeClass, isWeakScore } from "../../utils/badges";

interface EvidenceListProps {
  retrieved: RetrievedDoc[];
}

export default function EvidenceList({ retrieved }: EvidenceListProps) {
  if (retrieved.length === 0) {
    return (
      <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
        <div className="mb-1 text-[11.5px] font-bold text-[#94a3b8]">
          근거 문서 <span className="font-medium text-[#cbd5e1]">· RAG 검색 결과</span>
        </div>
        <p className="text-[13px] text-[#94a3b8]">관련 근거 문서를 찾지 못했어요.</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[#e2e8f0] bg-white px-[22px] py-5">
      <div className="mb-[13px] text-[11.5px] font-bold text-[#94a3b8]">
        근거 문서 <span className="font-medium text-[#cbd5e1]">· RAG 검색 결과</span>
      </div>

      <div className="flex flex-col gap-[11px]">
        {retrieved.map((r, i) => {
          const weak = isWeakScore(r.score);
          return (
            <div
              key={i}
              className="rounded-[11px] border border-[#e2e8f0] bg-[#fbfcfe] px-4 py-3.5"
            >
              <div className="mb-[7px] flex items-center justify-between gap-2.5">
                <span className="overflow-hidden text-ellipsis whitespace-nowrap font-mono text-[12px] font-bold text-[#475569]">
                  {r.source}
                </span>
                <span className={scoreBadgeClass(r.score)}>
                  유사도 {r.score.toFixed(3)}
                </span>
              </div>
              <p className="text-[13px] leading-relaxed text-[#64748b]">
                {r.content}
              </p>
              {weak && (
                <div className="mt-2 inline-flex items-center gap-1 rounded-md border border-[#fde68a] bg-[#fffbeb] px-2 py-[3px] text-[11px] font-extrabold text-[#d97706]">
                  ⚠ 근거 약함
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
