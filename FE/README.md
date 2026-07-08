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
├─ main.tsx                  # 진입점 (QueryClient + AuthProvider + Router 주입)
├─ App.tsx                   # 라우팅 (/login, /register, / = 일반, /admin = staff+master)
├─ index.css                 # Tailwind + 커스텀 애니메이션 (Pretendard는 index.html)
│
├─ types/
│  ├─ inquiry.ts             # 백엔드 응답 타입 (v4: 검토 데이터 확장 + 재배정)
│  └─ auth.ts                # 로그인/회원가입 타입 (Role: general/staff/master)
├─ constants/options.ts      # 예시 칩·필터·재배정 옵션·임계값
│
├─ api/
│  ├─ client.ts              # fetch 래퍼: 토큰 자동 첨부 + 401 시 자동 로그아웃 이벤트
│  ├─ auth.ts                # POST /api/auth/register, /api/auth/login
│  └─ inquiry.ts             # POST /api/inquiry, GET /my, GET /my/{id}, GET /pending,
│                             # PATCH /{id}/review, PATCH /{id}/rule (master 전용)
│
├─ context/AuthContext.tsx   # 로그인 세션 상태 (localStorage 저장, 401 이벤트 구독)
├─ lib/
│  ├─ queryClient.ts
│  └─ authStorage.ts         # localStorage 읽기/쓰기 + 전역 401 이벤트 발행
│
├─ hooks/
│  ├─ useSubmitInquiry.ts    # 문의 등록 (접수 확인만 옴)
│  ├─ useMyInquiries.ts      # 내 문의 목록 (로그인 기반, 검색 없음)
│  ├─ usePendingInquiries.ts # 검토 대기 목록 (staff 이상)
│  ├─ useReviewInquiry.ts    # 답변 승인 (그대로/수정, staff 이상)
│  └─ useUpdateRule.ts       # 부서/우선순위 재배정 (master 전용)
│
├─ utils/
│  ├─ badges.ts              # 배지/색상 → Tailwind 클래스 (근거 약함/확신도 포함)
│  └─ format.ts              # 날짜 표시·확신도 계산·우선순위 정렬
│
├─ pages/
│  ├─ LoginPage.tsx          # 로그인
│  ├─ RegisterPage.tsx       # 회원가입 (가입은 항상 general)
│  ├─ CitizenPage.tsx        # 일반 사용자: 입력 → 접수완료 → 내 문의함
│  └─ StaffPage.tsx          # staff/master: 검토 대기 목록 + 상세(승인 + 재배정)
│
└─ components/
   ├─ Header.tsx             # 로고 + 로그인한 사용자 정보(역할 라벨 3종) + 로그아웃
   ├─ ProtectedRoute.tsx     # 로그인 필요 + role 검사 라우트 가드
   ├─ common/Spinner.tsx
   ├─ citizen/
   │  ├─ InquiryForm.tsx     # 입력창 + 예시 칩
   │  ├─ SubmittedCard.tsx   # 접수 완료 (실제 문의 id 표시)
   │  ├─ MyInquiries.tsx     # 내 문의함 목록 (상태 필터: 전체/대기중/완료)
   │  └─ MyInquiryItem.tsx   # 목록 항목 (펼치면 답변 표시)
   └─ staff/
      ├─ Inbox.tsx           # 검토 대기 목록 (우선순위 필터 + 정렬)
      ├─ FilterBar.tsx
      ├─ InboxItem.tsx
      ├─ TicketDetail.tsx    # 원문 + 분류 + 룰 + 초안 + 근거문서 + 승인 액션
      ├─ ClassificationCard.tsx  # 유형·핵심요청·확신도바·분류불확실 경고·domain 태그
      ├─ RuleCard.tsx            # 우선순위·부서 (master만 편집 가능, staff는 읽기전용)
      ├─ DraftEditor.tsx         # 편집 가능한 AI 초안 + answer_confidence 배지
      ├─ EvidenceList.tsx        # RAG 근거 문서 (유사도/근거약함)
      └─ LlmErrorBanner.tsx      # LLM 실패 배너
```

---

## 5. 인증 흐름

- `/login`, `/register` 는 누구나 접근 가능.
- `/`(일반 사용자)는 `general`만, `/admin`(담당자 화면)은 `staff`와 `master` 둘 다 접근 가능.
  - 로그인 안 했으면 `/login` 으로 리다이렉트.
  - 로그인은 했지만 role 이 안 맞으면(`general`이 `/admin` 접근 등) 자기 홈으로 리다이렉트.
- 로그인 성공 시 `access_token` + `role` 을 `localStorage`(`aian_auth` 키)에 저장.
- 이후 모든 인증 필요 요청에 `Authorization: Bearer <토큰>` 자동 첨부 (`api/client.ts`).
- 토큰 만료/무효로 401 이 오면 `client.ts` 가 전역 이벤트(`aian:unauthorized`)를 쏘고,
  `AuthContext` 가 이를 구독해 자동 로그아웃 → 다음 렌더에서 `ProtectedRoute` 가 `/login` 으로 보냄.
- 회원가입은 항상 `role: general` 로 생성됨(서버가 강제). staff/master 계정은 백엔드 팀이 DB에서 직접 부여.

---

## 6. 권한 3단계 (v4)

```
general (일반 사용자)
   ↓
staff   (담당자)       — 검토 큐 조회, 답변 승인
   ↓
master  (최고관리자)   — + 부서/우선순위 재배정
```

계층형이라 `master`는 `staff`가 하는 것(검토 큐 조회, 답변 승인)도 다 할 수 있다.
화면은 하나(`/admin` = `StaffPage`)를 공유하고, `useAuth().role === "master"` 여부로
`RuleCard` 를 편집 가능하게 보여줄지, 읽기 전용으로 보여줄지만 갈린다.
staff 계정으로 `PATCH /api/inquiry/{id}/rule` 을 직접 호출하면 서버가 403을 주므로,
프론트에서도 아예 그 버튼을 안 보여줘서 헷갈릴 일이 없게 했다.

| 엔드포인트 | 필요 권한 |
|---|---|
| `POST /api/inquiry` | 로그인만 하면 됨 |
| `GET /api/inquiry/my`, `/my/{id}` | 로그인만 하면 됨 |
| `GET /api/inquiry/pending` | staff 이상 |
| `PATCH /api/inquiry/{id}/review` | staff 이상 |
| `PATCH /api/inquiry/{id}/rule` | **master만** |

---

## 7. 문의 처리 흐름

```
일반 사용자          POST /api/inquiry           담당자(staff+)
  등록  ───────────────────────────────▶   (답변 없음, 접수 확인 id만)
                                                    │
                                          GET /api/inquiry/pending
                                          (분류·근거문서·AI 초안·확신도 전부 확인)
                                                    │
                                    ┌───────────────┴────────────────┐
                                    │                                 │
                          PATCH .../review                  PATCH .../rule (master만)
                          (그대로 승인 / 수정 후 승인)         (부서·우선순위 재배정)
                                    │
  GET /api/inquiry/my ◀────────────┘
  (status: answered 로 바뀌고 answer 가 채워짐)
```

**일반 사용자 화면**
- 문의 등록 직후에는 AI 결과를 전혀 보여주지 않는다. `POST /api/inquiry` 응답은
  `{ id, message, created_at }` 뿐이라, 접수 완료 화면엔 이 `id`만 표시.
- "내 문의함"은 키워드 검색이 아니라 `GET /api/inquiry/my` 를 그대로 호출한다.
  `status: "pending"` 이면 "답변 대기중" 표시, `"answered"` 면 `answer` 를 펼쳐서 보여준다.

**담당자 화면(staff/master 공용)**
- 목록은 `GET /api/inquiry/pending` 실제 API로 채운다.
- v4부터 이 API 응답에 분류(`key_request`/`confidence`/`domain`), 근거 문서(`retrieved`),
  LLM 실패 여부(`used_llm`/`llm_error`)가 전부 복원되어 v1 디자인대로 카드들을 다시 그렸다.
- 승인 액션은 **"초안 그대로 승인"**(`final_answer: null`) 또는 초안을 고친 뒤
  **"수정한 내용으로 승인"**(`final_answer: 수정된 텍스트`) 두 가지.
- 승인하면 그 건은 `pending` 목록에서 즉시 빠진다(쿼리 무효화로 자동 새로고침).

**최고관리자 전용**
- `RuleCard` 가 편집 가능한 셀렉트 박스로 바뀌고, 값을 바꾸면 "재배정 저장" 버튼이 활성화된다.
- 저장 시 `PATCH /api/inquiry/{id}/rule` 호출, 성공하면 목록을 새로고침해서 바뀐 값을 반영한다.

**초안 임시 저장**
- 서버에 저장하지 않는다(백엔드팀 결정). 담당자 화면의 편집 중인 초안은 `StaffPage` 의
  로컬 state(`drafts`)에만 있으며, 새로고침하면 사라진다. 승인해야 서버에 반영된다.
