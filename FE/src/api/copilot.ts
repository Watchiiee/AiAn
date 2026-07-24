import { BASE_URL } from "./client";
import { getToken } from "../lib/authStorage";
import type { CopilotRequest } from "../types/copilot";

interface StreamCopilotCallbacks {
  /** 텍스트 조각이 도착할 때마다 호출. 이어붙이면 전체 답변이 된다. */
  onDelta: (text: string) => void;
  /** LLM 호출 자체가 실패했을 때(타임아웃 등). 이후 청크는 오지 않는다. */
  onError: (message: string) => void;
  /** 스트림이 정상 종료됐을 때([DONE] 수신) */
  onDone: () => void;
}

/**
 * 담당자 코파일럿에게 질문을 보내고 답변을 스트리밍으로 받는다.
 *
 * EventSource(브라우저 기본 SSE 클라이언트)는 GET만 지원하고 커스텀 헤더를
 * 못 보내서 이 엔드포인트(POST + JWT 헤더 필요)엔 못 쓴다. 그래서 fetch +
 * ReadableStream 으로 직접 파싱한다.
 *
 * 권한 참고: master가 아닌 일반 staff는 자기 부서로 배정된 문의에만 호출
 * 가능하다. 다른 부서 문의면 서버가 403을 준다 — 이 경우 onError로 전달된다.
 */
export async function streamCopilot(
  inquiryId: number,
  question: string,
  { onDelta, onError, onDone }: StreamCopilotCallbacks,
): Promise<void> {
  const token = getToken();
  const body: CopilotRequest = { question };

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/inquiry/${inquiryId}/copilot`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch {
    onError("네트워크 연결에 실패했어요. 다시 시도해 주세요.");
    return;
  }

  if (!res.ok || !res.body) {
    if (res.status === 403) {
      onError("이 문의를 조회할 권한이 없어요 (다른 부서로 배정된 문의예요).");
    } else {
      onError(`요청에 실패했어요 (HTTP ${res.status}).`);
    }
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // "data: ...\n\n" 단위로 자르기 (한 번에 여러 줄이 올 수 있다)
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? ""; // 마지막(미완성) 조각은 다음 루프로 넘김

      for (const part of parts) {
        const line = part.replace(/^data:\s*/, "").trim();
        if (!line) continue;
        if (line === "[DONE]") {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(line);
          if (parsed.delta) onDelta(parsed.delta);
          if (parsed.error) {
            onError(parsed.error);
            return;
          }
        } catch {
          // 파싱 실패한 조각은 무시 (버퍼 경계 이슈일 수 있음)
        }
      }
    }
    onDone();
  } catch {
    onError("응답을 받는 중 연결이 끊겼어요. 다시 시도해 주세요.");
  }
}