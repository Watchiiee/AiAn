import { useCallback, useEffect, useRef, useState } from "react";
import { streamCopilot } from "../api/copilot";
import type { CopilotMessage } from "../types/copilot";

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * 담당자 코파일럿 채팅 상태.
 * inquiryId 가 바뀌면(다른 문의를 선택하면) 대화를 초기화한다 — 백엔드가
 * 대화를 기억하지 않는 것과 마찬가지로, 문의를 옮기면 새 대화로 시작한다.
 */
export function useCopilotChat(inquiryId: number | null) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const lastQuestionRef = useRef<string>("");

  // 다른 문의를 선택하면 대화 초기화
  useEffect(() => {
    setMessages([]);
    setIsStreaming(false);
  }, [inquiryId]);

  const send = useCallback(
    (question: string) => {
      if (inquiryId === null || !question.trim() || isStreaming) return;
      lastQuestionRef.current = question;

      const userMsg: CopilotMessage = { id: makeId(), role: "user", content: question };
      const assistantId = makeId();
      const assistantMsg: CopilotMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      streamCopilot(inquiryId, question, {
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + delta } : m,
            ),
          );
        },
        onError: (message) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: message, streaming: false, failed: true }
                : m,
            ),
          );
          setIsStreaming(false);
        },
        onDone: () => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m)),
          );
          setIsStreaming(false);
        },
      });
    },
    [inquiryId, isStreaming],
  );

  const retryLast = useCallback(() => {
    if (!lastQuestionRef.current) return;
    // 실패한 마지막 user/assistant 쌍을 지우고 다시 보낸다
    setMessages((prev) => prev.slice(0, -2));
    send(lastQuestionRef.current);
  }, [send]);

  return { messages, isStreaming, send, retryLast };
}