# AiAn 프론트엔드

협회 민원 대응 AI 시스템의 프론트엔드.
Vite + React + TypeScript + Tailwind + React Query + React Router.

---

## 1. 처음 세팅 (터미널)

이미 만들어 둔 `TEST/FE` 폴더 안에서 진행합니다.

```bash
cd TEST/FE

# 1) Vite + React + TS 스캐폴딩 (현재 폴더에 바로)
npm create vite@latest . -- --template react-ts

# 2) 의존성 설치
npm install

# 3) 이 프로젝트가 쓰는 라이브러리
npm install @tanstack/react-query react-router-dom
npm install -D tailwindcss @tailwindcss/vite
```

> Tailwind v4 기준입니다. (설정 파일 없이 Vite 플러그인 + CSS `@import`만으로 동작)
> 만약 팀이 v3 를 쓰기로 했다면 `src/index.css` 맨 위 주석 참고.

---

## 2. 기본 생성 파일 중 지울 것 / 덮어쓸 것

`npm create vite` 가 만든 보일러플레이트 중 아래는 **삭제**합니다.

```bash
rm src/App.css          # 안 씀 (스타일은 Tailwind + index.css)
rm src/assets/react.svg # 기본 로고 이미지
rm public/vite.svg      # 기본 파비콘
rmdir src/assets 2>/dev/null || true
```

아래는 이 저장소 파일로 **덮어씁니다** (그대로 복사해 넣으면 됨):

- `src/App.tsx`
- `src/main.tsx`
- `src/index.css`
- `index.html`
- `vite.config.ts`
- `src/vite-env.d.ts`

그 외 `src/` 하위 폴더(`api`, `types`, `constants`, `mock`, `hooks`, `utils`, `lib`,
`pages`, `components`)는 새로 추가되는 파일들입니다.

---

## 3. 실행

```bash
# 프론트 개발 서버
npm run dev          # http://localhost:5173

# (별도 터미널) 백엔드
#   레포 루트에서:  python3 -m uvicorn BE.main:app
```

`.env.development` 의 `VITE_API_BASE` 가 백엔드 주소(`http://localhost:8000`)를 가리킵니다.
포트가 다르면 이 값과 백엔드의 `allow_origins` 를 맞춰 주세요.

---

## 4. 폴더 구조

```
src/
├─ main.tsx                  # 진입점 (QueryClient + Router 주입)
├─ App.tsx                   # 라우팅 (/ = 민원인, /admin = 담당자)
├─ index.css                 # Tailwind + Pretendard + 커스텀 애니메이션
│
├─ types/inquiry.ts          # 백엔드 응답 타입 (API 스펙 그대로)
├─ constants/options.ts      # 부서·우선순위·칩·임계값
├─ mock/tickets.ts           # 담당자 인박스 목업 (백엔드 목록 API 생기면 교체)
│
├─ api/
│  ├─ client.ts              # fetch 래퍼 (VITE_API_BASE)
│  └─ inquiry.ts             # POST /api/inquiry
│
├─ hooks/
│  ├─ useSubmitInquiry.ts    # 문의 제출 (react-query mutation)
│  └─ useTickets.ts          # 인박스 목록 (react-query query, 지금은 목업)
│
├─ lib/queryClient.ts        # React Query 설정
├─ utils/
│  ├─ badges.ts              # 배지/색상 → Tailwind 클래스
│  └─ format.ts              # 접수번호·확신도·정렬
│
├─ pages/
│  ├─ CitizenPage.tsx        # 민원인: 입력 → 접수완료 → 조회
│  └─ StaffPage.tsx          # 담당자: 인박스 + 상세 (편집 상태 관리)
│
└─ components/
   ├─ Header.tsx             # 로고 + 역할 전환 탭
   ├─ common/Spinner.tsx
   ├─ citizen/
   │  ├─ InquiryForm.tsx     # 입력창 + 예시 칩
   │  ├─ SubmittedCard.tsx   # 접수 완료 (접수번호)
   │  └─ LookupPanel.tsx     # 내 문의 조회
   └─ staff/
      ├─ Inbox.tsx           # 인박스 (필터 + 정렬)
      ├─ FilterBar.tsx
      ├─ InboxItem.tsx
      ├─ TicketDetail.tsx    # 상세 (아래 카드들 조합)
      ├─ ClassificationCard.tsx  # AI 분류 + 확신도 바
      ├─ RuleCard.tsx            # 우선순위·부서 재배정
      ├─ DraftEditor.tsx         # 편집 가능한 AI 초안
      ├─ EvidenceList.tsx        # RAG 근거 문서 (유사도/근거약함)
      └─ LlmErrorBanner.tsx      # LLM 실패 배너
```

---

## 5. 백엔드 연동 메모

- **민원인 화면**은 AI 결과(초안·근거)를 보여주지 않습니다. 제출 → "접수 완료"만.
  (제출 자체는 실제 `POST /api/inquiry` 를 호출하지만 응답의 AI 내용은 쓰지 않음)
- **담당자 화면**은 지금 목업(`mock/tickets.ts`)으로 목록을 보여줍니다.
  백엔드에 목록 조회 API(예: `GET /api/inquiries`)가 생기면
  `hooks/useTickets.ts` 의 `queryFn` 만 fetch 로 바꾸면 됩니다.
- `llm_error` 가 있으면 상세 상단에 실패 배너, `answer_draft` 는 비어 담당자가 직접 작성.
- `retrieved[].score <= 0.4` 면 "근거 약함", `confidence < 0.5` 면 "분류 불확실".
