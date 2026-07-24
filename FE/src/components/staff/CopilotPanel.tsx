import { useEffect, useRef, useState } from "react";
import { useCopilotChat } from "../../hooks/useCopilotChat";

interface CopilotPanelProps {
  inquiryId: number;
  onClose: () => void;
}

const SUGGESTIONS = [
  "왜 이 문서를 선택했어?",
  "확신도가 왜 이렇게 나왔어?",
  "이 부분은 어느 문서 내용이야?",
];

export default function CopilotPanel({ inquiryId, onClose }: CopilotPanelProps) {
  const { messages, isStreaming, send, retryLast } = useCopilotChat(inquiryId);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    const q = input.trim();
    if (!q || isStreaming) return;
    send(q);
    setInput("");
  }

  /** 예시 질문은 그대로 보내지 않고 입력창에 채워준다 — 어디까지나 "예시"일 뿐,
   *  실제 전송은 사용자가 직접 입력창에서 하도록 동일한 경로를 쓰게 한다. */
  function fillSuggestion(text: string) {
    setInput(text);
    inputRef.current?.focus();
  }

  const lastMsg = messages[messages.length - 1];
  const waitingForFirstDelta =
    isStreaming && lastMsg?.role === "assistant" && lastMsg.content === "";

  return (
    <aside className="flex w-[340px] flex-none flex-col border-l border-[#e2e8f0] bg-white">
      <div className="flex h-[52px] flex-none items-center justify-between border-b border-[#f1f5f9] px-4">
        <div className="flex items-center gap-1.5">
          <span className="text-[13.5px] font-extrabold text-[#1e293b]">
            🤖 AI 코파일럿
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md px-1.5 py-0.5 text-[13px] font-bold text-[#94a3b8] hover:bg-[#f1f5f9] hover:text-[#64748b]"
        >
          ✕
        </button>
      </div>

      <div ref={scrollRef} className="aian-scroll flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="rounded-[11px] border border-[#e2e8f0] bg-[#f8fafc] px-3.5 py-3.5">
            <p className="mb-2.5 text-[12.5px] leading-relaxed text-[#64748b]">
              이 문의 화면에 나온 내용(분류·근거 문서·초안)에 대해 물어보세요.
              새로운 검색이나 다른 문의 조회는 아직 못 해요.
            </p>
            <p className="mb-1.5 text-[11px] font-bold text-[#94a3b8]">
              예시 (누르면 입력창에 채워져요 · 직접 입력도 가능)
            </p>
            <div className="flex flex-col gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => fillSuggestion(s)}
                  className="rounded-[8px] border border-[#e2e8f0] bg-white px-2.5 py-2 text-left text-[12px] font-medium text-[#334155] hover:bg-[#f1f5f9]"
                >
                  💡 {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {messages.map((m) => (
            <div
              key={m.id}
              className={[
                "max-w-[92%] rounded-[12px] px-3 py-2.5 text-[13px] leading-relaxed",
                m.role === "user"
                  ? "ml-auto bg-[#2563eb] text-white"
                  : m.failed
                    ? "border border-[#fecaca] bg-[#fef2f2] text-[#b91c1c]"
                    : "border border-[#e2e8f0] bg-[#f8fafc] text-[#1e293b]",
              ].join(" ")}
            >
              {m.content}
              {m.streaming && m.content !== "" && (
                <span className="ml-0.5 inline-block h-[13px] w-[2px] animate-pulse bg-[#94a3b8] align-middle" />
              )}
              {m.failed && (
                <button
                  type="button"
                  onClick={retryLast}
                  className="mt-1.5 block text-[11.5px] font-bold text-[#dc2626] underline"
                >
                  다시 시도
                </button>
              )}
            </div>
          ))}

          {waitingForFirstDelta && (
            <div className="flex items-center gap-1.5 rounded-[12px] border border-[#e2e8f0] bg-[#f8fafc] px-3 py-2.5 text-[12.5px] text-[#94a3b8]">
              <span className="inline-block h-[6px] w-[6px] animate-bounce rounded-full bg-[#cbd5e1] [animation-delay:-0.2s]" />
              <span className="inline-block h-[6px] w-[6px] animate-bounce rounded-full bg-[#cbd5e1]" />
              <span className="inline-block h-[6px] w-[6px] animate-bounce rounded-full bg-[#cbd5e1] [animation-delay:0.2s]" />
              <span className="ml-1">생각 중…</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-none border-t border-[#f1f5f9] p-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="이 문의에 대해 물어보세요"
            disabled={isStreaming}
            className="min-h-[38px] max-h-[90px] flex-1 resize-none rounded-[9px] border border-[#cbd5e1] px-2.5 py-2 text-[13px] outline-none focus:border-[#2563eb] disabled:bg-[#f8fafc]"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="flex-none rounded-[9px] bg-[#2563eb] px-3.5 py-2 text-[12.5px] font-bold text-white hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-40"
          >
            전송
          </button>
        </div>
      </div>
    </aside>
  );
}
