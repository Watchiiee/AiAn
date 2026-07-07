import { useState } from "react";
import InquiryForm from "../components/citizen/InquiryForm";
import SubmittedCard from "../components/citizen/SubmittedCard";
import LookupPanel from "../components/citizen/LookupPanel";
import Spinner from "../components/common/Spinner";
import { useSubmitInquiry } from "../hooks/useSubmitInquiry";
import { generateTicketNo } from "../utils/format";

type View = "form" | "done" | "lookup";

export default function CitizenPage() {
  const [view, setView] = useState<View>("form");
  const [ticketNo, setTicketNo] = useState<string | null>(null);
  const submit = useSubmitInquiry();

  function handleSubmit(text: string) {
    submit.mutate(text, {
      onSuccess: () => {
        // 민원인은 AI 결과를 보지 않는다. 접수 확인 + 접수번호만.
        setTicketNo(generateTicketNo());
        setView("done");
      },
    });
  }

  return (
    <main className="aian-scroll flex flex-1 justify-center overflow-y-auto px-[18px] pb-[60px] pt-[34px]">
      <div className="w-full max-w-[560px]">
        {submit.isPending ? (
          <div className="flex flex-col items-center justify-center py-[90px] text-center">
            <Spinner />
            <p className="mb-1 mt-[22px] text-[16px] font-bold">접수 처리 중…</p>
            <p className="text-[13px] text-[#94a3b8]">잠시만 기다려 주세요</p>
          </div>
        ) : view === "form" ? (
          <>
            <InquiryForm
              onSubmit={handleSubmit}
              onGoLookup={() => setView("lookup")}
            />
            {submit.isError && (
              <p className="mt-4 rounded-xl border border-[#fecaca] bg-[#fef2f2] p-3 text-center text-[13px] font-semibold text-[#dc2626]">
                접수 중 문제가 발생했어요. 잠시 후 다시 시도해 주세요.
              </p>
            )}
          </>
        ) : view === "done" && ticketNo ? (
          <SubmittedCard
            ticketNo={ticketNo}
            onNewInquiry={() => {
              submit.reset();
              setView("form");
            }}
            onGoLookup={() => setView("lookup")}
          />
        ) : (
          <LookupPanel onBack={() => setView("form")} />
        )}
      </div>
    </main>
  );
}
