"""
핵심 파이프라인 — LangGraph 버전.

기존(plain Python) 구현은 pipeline_legacy.py 에 보존.
외부 인터페이스(process_inquiry(text) -> InquiryResponse)는 동일하게 유지해
BE/api/inquiry.py 등 호출부는 전혀 바뀌지 않는다.

그래프 구조:
    START → classify → rule → retrieve ─┬─(score < 임계값)→ no_evidence → END
                                          └─(score 충분)────→ generate ──→ END

- classify/rule/retrieve/generate 노드는 AI/BE 의 기존 함수를 그대로 재사용한다
  (LangGraph로 바꾼 것은 '흐름을 연결하는 방식'이며, 각 단계의 로직 자체는 안 바뀜).
- score 조기차단(근거 없는 질문 필터)을 조건부 엣지로 명시적으로 표현한 것이
  plain 버전과의 가장 큰 차이 — 분기 구조가 그래프 위에 눈에 보이게 드러난다.
"""
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from AI.llm import LLMError
from BE.core.config import settings
from BE.core.schemas import InquiryResponse, AnswerConfidence, Classification, RuleResult, RetrievedDoc
from BE.rules.rule_engine import apply_rules
from AI.classifier.classifier import classify
from AI.rag.retriever import retrieve
from AI.rag.generator import generate, fallback_answer, _top_score


class PipelineState(TypedDict):
    """그래프의 노드들이 공유하는 상태."""
    text: str
    cls: Optional[Classification]
    rule: Optional[RuleResult]
    docs: Optional[list[RetrievedDoc]]
    answer: Optional[str]
    answer_confidence: Optional[AnswerConfidence]
    llm_error: Optional[str]


# --- 노드 ---

def node_classify(state: PipelineState) -> dict:
    return {"cls": classify(state["text"])}


def node_rule(state: PipelineState) -> dict:
    return {"rule": apply_rules(state["text"], state["cls"])}


def node_retrieve(state: PipelineState) -> dict:
    return {"docs": retrieve(state["text"], state["cls"])}


def node_generate(state: PipelineState) -> dict:
    """근거가 충분할 때만 도달하는 노드. LLM 호출."""
    try:
        answer, conf = generate(state["text"], state["cls"], state["rule"], state["docs"])
        return {"answer": answer, "answer_confidence": conf, "llm_error": None}
    except LLMError as e:
        err = str(e)
        answer = fallback_answer(state["text"], state["cls"], state["rule"], state["docs"], reason=err)
        return {"answer": answer, "answer_confidence": AnswerConfidence.PARTIAL, "llm_error": err}


def node_no_evidence(state: PipelineState) -> dict:
    """검색 최고 score 가 임계값 미달일 때 도달. LLM을 부르지 않고 즉시 종료."""
    rule = state["rule"]
    answer = (
        "안녕하세요. 문의하신 내용은 현재 보유한 자료에서 정확한 근거를 찾기 어렵습니다.\n\n"
        f"정확한 안내를 위해 {rule.department}에서 확인 후 회신드리겠습니다. 감사합니다."
    )
    return {"answer": answer, "answer_confidence": AnswerConfidence.INSUFFICIENT, "llm_error": None}


def _route_after_retrieve(state: PipelineState) -> str:
    """조건부 엣지: 근거가 명백히 부족하면 LLM 호출 없이 바로 종료 경로로."""
    if _top_score(state["docs"]) < settings.no_evidence_threshold:
        return "no_evidence"
    return "generate"


# --- 그래프 구성 ---

def _build_graph():
    g = StateGraph(PipelineState)
    g.add_node("classify", node_classify)
    g.add_node("rule", node_rule)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", node_generate)
    g.add_node("no_evidence", node_no_evidence)

    g.add_edge(START, "classify")
    g.add_edge("classify", "rule")
    g.add_edge("rule", "retrieve")
    g.add_conditional_edges(
        "retrieve", _route_after_retrieve, {"generate": "generate", "no_evidence": "no_evidence"}
    )
    g.add_edge("generate", END)
    g.add_edge("no_evidence", END)
    return g.compile()


_graph = _build_graph()


def process_inquiry(text: str) -> InquiryResponse:
    """외부에서 보는 인터페이스는 기존과 동일 (LangGraph 사용은 내부 구현 세부사항)."""
    result: PipelineState = _graph.invoke({"text": text})

    cls = result["cls"]
    return InquiryResponse(
        original_text=text,
        classification=cls,
        rule=result["rule"],
        retrieved=result["docs"],
        answer_draft=result["answer"],
        answer_confidence=result["answer_confidence"],
        used_llm=settings.has_api_key and result["llm_error"] is None,
        llm_error=result["llm_error"],
    )