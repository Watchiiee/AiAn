"""
핵심 파이프라인 — LangGraph 심화(Adaptive RAG) 버전.

외부 인터페이스(process_inquiry(text) -> InquiryResponse)는 계속 동일하게
유지해 inquiry.py/DB/인증 등 호출부는 전혀 바뀌지 않는다.

그래프 구조:

    START → classify → rule → check_urgency
                                    │ (is_urgent면 rule.priority='긴급'로만 표시.
                                    │  RAG는 긴급/비긴급 구분 없이 항상 그대로 진행 —
                                    │  "초안 생성"과 "담당자 화면 노출 순서"는 별개 문제)
                                    ▼
                          ┌─(is_relevant=False, 잡담)──→ chitchat_decline ─→ END
                          └─(그 외 전부, RAG 경로)
                                    │
                                    ▼
                                retrieve
                                    │
                                    ▼
                               doc_grade ──(관련없음, rewrite<2)──→ rewrite_query ─┐
                                    │                                              │
                                    │                                   (retrieve로 루프)
                           (관련있음)│
                                    │        (관련없음, rewrite 소진)
                                    │              └──────────────────→ no_evidence → END
                                    ▼
                                generate
                                    │
                                    ▼
                           hallucination_grade ──(실패, regen<2)──→ bump_regenerate ─┐
                                    │                                                 │
                           (근거일치)│                                      (generate로 루프)
                                    ▼
                              answer_grade ──(부적합, regen<2)──→ bump_regenerate (위와 공유)
                                    │
                           (적합)   ▼
                                finalize ──→ END
                           (재시도 소진 시 finalize에서 확신도 하향 조정)

- check_urgency는 독립된 LLM 호출로 "긴급 여부"만 판단한다 (분류 프롬프트에
  섞지 않음 — 여러 판단을 한 프롬프트에 몰아넣으면 필드가 혼동됐던 전례가 있어
  판단 하나당 호출 하나 원칙을 지킨다). 키워드 매칭은 쓰지 않는다("긴급! 사랑해요"
  같은 문장에 단어만 있고 실제로는 무관한 경우를 잡아내지 못하는 거짓양성 위험이
  있어서다). is_urgent=True이면서 구체적 근거(urgent_reason)가 있을 때만 인정한다.
- [설계 변경] 과거에는 is_urgent=True면 RAG를 완전히 건너뛰고 정형 안내문만 만들어
  담당자에게 넘겼다(urgent_escalate 노드). 멘토링 피드백을 반영해 제거함 — 이유:
  ① 진짜 재난·안전사고라면 초안 생성(수 초)이 담당자의 실제 대응 속도를 늦추지
  않고, ② "긴급"이 문맥상 격한 어투일 뿐 실제로는 일반 민원인 경우, RAG를 건너뛰면
  이 시스템의 핵심 가치(초안 자동생성)를 오히려 못 받는 역설이 생긴다. 그래서
  "RAG를 거치느냐"와 "담당자 화면에서 얼마나 먼저 보이느냐"를 분리했다 — 후자는
  rule.priority='긴급' 값으로 `/inquiry/pending` 정렬에서 처리한다(BE/db/crud.py).
- 재검색(rewrite) 최대 2회, 재생성(hallucination/answer 실패 → generate) 최대 2회
  (두 grader가 카운터 공유).
"""
import os
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from AI.llm import LLMError
from BE.core.config import settings
from BE.core.schemas import (
    InquiryResponse, AnswerConfidence, Classification, RuleResult, RetrievedDoc,
)
from BE.rules.rule_engine import apply_rules
from AI.classifier.classifier import classify
from AI.rag.retriever import retrieve
from AI.rag.generator import generate, fallback_answer, _top_score
from AI.rag.grading import (
    grade_documents, grade_documents_individual, grade_hallucination, grade_answer,
    rewrite_query, check_urgency,
)

_MAX_REWRITE = 2
_MAX_REGENERATE = 2


def _get_langfuse_callbacks() -> list:
    """
    Langfuse 트레이싱 콜백. 키가 없으면 빈 리스트(트레이싱 없이 정상 동작) —
    관측은 부가 기능이라 필수가 아니다 (DB 저장 실패해도 API가 안 죽는 것과 같은 원칙).
    """
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return []
    try:
        import os
        # langfuse 공식 SDK는 환경변수로 키를 읽는다 (.env 값을 그대로 넘겨줌)
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
        from langfuse.langchain import CallbackHandler
        return [CallbackHandler()]
    except Exception:
        return []


class PipelineState(TypedDict):
    text: str
    search_query: str
    cls: Optional[Classification]
    rule: Optional[RuleResult]
    docs: Optional[list[RetrievedDoc]]
    graded_docs: Optional[list[RetrievedDoc]]  # doc_grade가 실제로 사용 승인한 부분집합
                                                 # (all_or_nothing 모드에서는 docs와 동일,
                                                 # individual 모드에서는 개별선별된 것만)
    answer: Optional[str]
    answer_confidence: Optional[AnswerConfidence]
    llm_error: Optional[str]
    route: str
    is_urgent: bool
    urgent_reason: Optional[str]
    doc_relevant: bool
    rewrite_count: int
    hallucination_ok: bool
    answer_ok: bool
    regenerate_count: int


# --- 분류·룰·긴급판정 ---

def node_classify(state: PipelineState) -> dict:
    cls = classify(state["text"])
    return {"cls": cls, "search_query": state["text"]}


def node_rule(state: PipelineState) -> dict:
    return {"rule": apply_rules(state["text"], state["cls"])}


def node_check_urgency(state: PipelineState) -> dict:
    """
    독립된 LLM 호출로 긴급 여부만 판단. 키워드 매칭 없음 — 문맥 기반 판단 +
    구체적 근거(urgent_reason)가 있을 때만 인정한다 (근거 없는 판단은 신뢰 안 함).
    """
    is_urgent, reason = check_urgency(state["text"])
    if is_urgent:
        rule = state["rule"].model_copy(update={"priority": "긴급", "urgent_reason": reason})
        return {"is_urgent": True, "urgent_reason": reason, "rule": rule}
    return {"is_urgent": False, "urgent_reason": None}


def _route_after_urgency(state: PipelineState) -> str:
    """
    라우터: 잡담이면 chitchat_decline, 그 외(긴급 포함)는 항상 RAG.
    과거에는 is_urgent=True를 여기서 분기해 RAG를 건너뛰었으나 제거함(모듈
    docstring의 [설계 변경] 참고) — 긴급 여부는 라우팅이 아니라 rule.priority
    값으로만 반영되고, 담당자 화면 정렬(BE/db/crud.py)에서 소비된다.
    """
    if not state["cls"].is_relevant:
        return "chitchat"
    return "rag"


def node_chitchat_decline(state: PipelineState) -> dict:
    """
    업무 무관 잡담: RAG를 건너뛰어 비용을 아끼고 정중히 안내.

    rule 노드가 만든 RuleResult는 category=OTHER 라서 기본적으로
    department_certain=False(부서 재배정 필요)로 잡혀있는데, 이건 잡담엔
    안 맞는 신호다 — 재배정할 '맞는 부서'가 원래 없는 경우이기 때문.
    담당자에게 "재배정하라"고 하는 대신 "잡담으로 자동 응대됨"으로 명확히
    구분해서, department_certain=True(이 판정 자체는 확실함) + 안내문구로 덮어쓴다.
    """
    rule = state["rule"]
    answer = (
        "안녕하세요. 협회 업무(전기안전관리자 선·해임, 경력, 감리, 공제, 교육 등)와 관련된 "
        "문의를 남겨주시면 자세히 안내드리겠습니다."
    )
    updated_rule = rule.model_copy(update={
        "department_certain": True,
        "department_note": "업무와 무관한 문의로 판단되어 안내 문구로 자동 응대되었습니다.",
    })
    return {"route": "chitchat", "rule": updated_rule, "answer": answer,
            "answer_confidence": AnswerConfidence.INSUFFICIENT, "docs": [], "graded_docs": [], "llm_error": None}


# --- RAG 경로: 검색 → 근거채점 → (재검색) → 답변생성 → 환각/적합성 채점 → (재생성) ---

def node_retrieve(state: PipelineState) -> dict:
    docs = retrieve(state["search_query"], state["cls"])
    return {"docs": docs, "route": "rag"}


# 비교실험용 스위치 ③: RAG_DOC_GRADE_MODE=all_or_nothing 이면 기존 방식(검색된 것
# 전체를 한 번에 관련있다/없다로만 판단)으로 되돌아간다. 기본값은 "individual"
# (개별 선별) — 89개 골든셋 전체 파이프라인 실측 결과(eval_pipeline_doc_grade.py)
# all_or_nothing이 recall 19.1%(insufficient 71/89)까지 무너졌던 반면 individual은
# recall 86.5%(insufficient 7/89)로 거의 완전히 회복시켜 기본값으로 승격함
# (DECISION_LOG R절 참고). 원인은 min_k=6으로 검색결과가 늘어난 뒤, all_or_nothing이
# "6개 전체가 관련있냐"는 이진판단을 반복 실패하며 재시도를 소진해 no_evidence로
# 끝나는 경우가 급증한 것으로 확인됨(도입 시점 회귀, 두 컴포넌트 경계에서 발생).
DOC_GRADE_MODE = os.environ.get("RAG_DOC_GRADE_MODE", "individual")


def node_doc_grade(state: PipelineState) -> dict:
    docs = state["docs"]
    if _top_score(docs) < settings.no_evidence_threshold:
        return {"doc_relevant": False, "graded_docs": []}

    if DOC_GRADE_MODE == "individual":
        selected_idx = grade_documents_individual(state["text"], docs)
        graded = [docs[i] for i in selected_idx]
        return {"doc_relevant": bool(graded), "graded_docs": graded}

    relevant = grade_documents(state["text"], docs)
    return {"doc_relevant": relevant, "graded_docs": docs if relevant else []}


def _route_after_doc_grade(state: PipelineState) -> str:
    if state["doc_relevant"]:
        return "generate"
    if state["rewrite_count"] < _MAX_REWRITE:
        return "rewrite"
    return "no_evidence"


def node_rewrite_query(state: PipelineState) -> dict:
    new_query = rewrite_query(state["text"])
    return {"search_query": new_query, "rewrite_count": state["rewrite_count"] + 1}


def node_no_evidence(state: PipelineState) -> dict:
    rule = state["rule"]
    answer = (
        "안녕하세요. 문의하신 내용은 현재 보유한 자료에서 정확한 근거를 찾기 어렵습니다.\n\n"
        f"정확한 안내를 위해 {rule.department}에서 확인 후 회신드리겠습니다. 감사합니다."
    )
    return {"answer": answer, "answer_confidence": AnswerConfidence.INSUFFICIENT, "llm_error": None}


def node_generate(state: PipelineState) -> dict:
    docs = state.get("graded_docs") or state["docs"]
    try:
        answer, conf = generate(state["text"], state["cls"], state["rule"], docs)
        return {"answer": answer, "answer_confidence": conf, "llm_error": None}
    except LLMError as e:
        err = str(e)
        answer = fallback_answer(state["text"], state["cls"], state["rule"], docs, reason=err)
        return {"answer": answer, "answer_confidence": AnswerConfidence.PARTIAL, "llm_error": err}


def node_hallucination_grade(state: PipelineState) -> dict:
    if state["llm_error"]:
        return {"hallucination_ok": True}
    docs = state.get("graded_docs") or state["docs"]
    return {"hallucination_ok": grade_hallucination(state["answer"], docs)}


def _route_after_hallucination(state: PipelineState) -> str:
    if state["hallucination_ok"]:
        return "answer_grade"
    if state["regenerate_count"] < _MAX_REGENERATE:
        return "bump_regenerate"
    return "answer_grade"


def node_answer_grade(state: PipelineState) -> dict:
    if state["llm_error"]:
        return {"answer_ok": True}
    return {"answer_ok": grade_answer(state["text"], state["answer"])}


def _route_after_answer_grade(state: PipelineState) -> str:
    if state["answer_ok"]:
        return "finalize"
    if state["regenerate_count"] < _MAX_REGENERATE:
        return "bump_regenerate"
    return "finalize"


def node_bump_regenerate(state: PipelineState) -> dict:
    return {"regenerate_count": state["regenerate_count"] + 1}


def node_finalize(state: PipelineState) -> dict:
    if not state.get("hallucination_ok", True) or not state.get("answer_ok", True):
        if state["answer_confidence"] == AnswerConfidence.SUFFICIENT:
            return {"answer_confidence": AnswerConfidence.PARTIAL}
    return {}


# --- 그래프 구성 ---

def _build_graph():
    g = StateGraph(PipelineState)
    g.add_node("classify", node_classify)
    g.add_node("rule", node_rule)
    g.add_node("check_urgency", node_check_urgency)
    g.add_node("chitchat_decline", node_chitchat_decline)
    g.add_node("retrieve", node_retrieve)
    g.add_node("doc_grade", node_doc_grade)
    g.add_node("rewrite_query", node_rewrite_query)
    g.add_node("no_evidence", node_no_evidence)
    g.add_node("generate", node_generate)
    g.add_node("hallucination_grade", node_hallucination_grade)
    g.add_node("answer_grade", node_answer_grade)
    g.add_node("bump_regenerate", node_bump_regenerate)
    g.add_node("finalize", node_finalize)

    g.add_edge(START, "classify")
    g.add_edge("classify", "rule")
    g.add_edge("rule", "check_urgency")
    g.add_conditional_edges("check_urgency", _route_after_urgency, {
        "chitchat": "chitchat_decline", "rag": "retrieve",
    })
    g.add_edge("chitchat_decline", END)

    g.add_edge("retrieve", "doc_grade")
    g.add_conditional_edges("doc_grade", _route_after_doc_grade, {
        "generate": "generate", "rewrite": "rewrite_query", "no_evidence": "no_evidence",
    })
    g.add_edge("rewrite_query", "retrieve")
    g.add_edge("no_evidence", END)

    g.add_edge("generate", "hallucination_grade")
    g.add_conditional_edges("hallucination_grade", _route_after_hallucination, {
        "answer_grade": "answer_grade", "bump_regenerate": "bump_regenerate",
    })
    g.add_conditional_edges("answer_grade", _route_after_answer_grade, {
        "finalize": "finalize", "bump_regenerate": "bump_regenerate",
    })
    g.add_edge("bump_regenerate", "generate")
    g.add_edge("finalize", END)

    return g.compile()


_graph = _build_graph()


def process_inquiry(text: str) -> InquiryResponse:
    """외부 인터페이스는 기존과 동일. LangGraph 사용은 내부 구현 세부사항."""
    init: PipelineState = {
        "text": text, "search_query": text, "cls": None, "rule": None, "docs": None,
        "graded_docs": None,
        "answer": None, "answer_confidence": None, "llm_error": None, "route": "",
        "is_urgent": False, "urgent_reason": None,
        "doc_relevant": False, "rewrite_count": 0, "hallucination_ok": True,
        "answer_ok": True, "regenerate_count": 0,
    }
    result: PipelineState = _graph.invoke(
        init, config={"callbacks": _get_langfuse_callbacks(), "run_name": "process_inquiry"}
    )

    docs = result["docs"] or []
    graded = result.get("graded_docs") or []
    # 검색된 전체(docs)는 그대로 다 보여주되, doc_grade가 실제로 답변에 쓰기로
    # 선택한 것만 selected=True로 표시 (개별선별 모드가 아니면 graded==docs라
    # 전부 True가 되어 예전 동작과 동일함).
    retrieved = [d.model_copy(update={"selected": d in graded}) for d in docs]

    return InquiryResponse(
        original_text=text,
        classification=result["cls"],
        rule=result["rule"],
        retrieved=retrieved,
        answer_draft=result["answer"],
        answer_confidence=result["answer_confidence"],
        used_llm=settings.has_api_key and result["llm_error"] is None,
        llm_error=result["llm_error"],
    )