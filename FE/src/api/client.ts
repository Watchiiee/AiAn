// 얇은 fetch 래퍼. baseURL 은 .env 의 VITE_API_BASE 로 바꿀 수 있다.
// 예) .env.development -> VITE_API_BASE=http://localhost:8000

const BASE_URL = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiPost<TBody, TResponse>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    // 백엔드 문서상 LLM 실패도 200 으로 오므로, 여기서 걸리는 건 진짜 네트워크/서버 오류다.
    throw new ApiError(
      `요청에 실패했어요 (HTTP ${res.status})`,
      res.status,
    );
  }

  return (await res.json()) as TResponse;
}
