"""
핵심 파이프라인 — LangGraph 심화(Adaptive RAG) 버전.

이전 단계 백업:
  pipeline_legacy.py       순수 Python 버전 (LangGraph 도입 전)
  pipeline_basic_graph.py  LangGraph 기본형 (분기 없는 라우터, grader 없음)
외부 인터페이스(process_inquiry(text) -> InquiryResponse)는 계속 동일하게
유지해 inquiry.py/DB/인증 등 호출부는 전혀 바뀌지 않는다.

그래프 구조:

    START → classify → rule ─┬─(urgent 키워드)──────────────→ urgent_escalate ──→ END
                              ├─(is_relevant=False, 잡담)────→ chitchat_decline ─→ END
                              └─(일반 업무 문의, RAG 경로)
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

- 재검색(rewrite) 최대 2회, 재생성(hallucination/answer 실패 → generate) 최대 2회(두 grader가 카운터 공유).
- urgent/chitchat 경로는 RAG·LLM 답변생성을 건너뛰어 비용을 아끼고,
  민감한 민원에 AI가 즉석 답변을 지어내는 위험도 피한다.
"""
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from AI.llm import LLMError
from BE.core.config import settings
from BE.core.schemas import (
    InquiryResponse, AnswerConfidence, Classification, RuleResult, RetrievedDoc,
)
from BE.rules.rule_engine import apply_rules, _URGENT_KEYWORDS
from AI.classifier.classifier import classify
from AI.rag.retriever import retrieve
from AI.rag.generator import generate, fallback_answer, _top_score
from AI.rag.grading import grade_documents, grade_hallucination, grade_answer, rewrite_query

_MAX_REWRITE = 2
_MAX_REGENERATE = 2


class PipelineState(TypedDict):
    text: str                                   # 원문 (검색에는 search_query 사용)
    search_query: str                           # 재검색 시 바뀌는 검색어 (초기값 = text)
    cls: Optional[Classification]
    rule: Optional[RuleResult]
    docs: Optional[list[RetrievedDoc]]
    answer: Optional[str]
    answer_confidence: Optional[AnswerConfidence]
    llm_error: Optional[str]
    route: str                                  # 추적용: urgent/chitchat/rag
    doc_relevant: bool
    rewrite_count: int
    hallucination_ok: bool
    answer_ok: bool
    regenerate_count: int


# --- 분류·룰 ---

def node_classify(state: PipelineState) -> dict:
    cls = classify(state["text"])
    return {"cls": cls, "search_query": state["text"]}


def node_rule(state: PipelineState) -> dict:
    return {"rule": apply_rules(state["text"], state["cls"])}


def _route_after_rule(state: PipelineState) -> str:
    """1단계 라우터: 긴급/잡담/일반업무 3분기."""
    if any(k in state["text"] for k in _URGENT_KEYWORDS):
        return "urgent"
    if not state["cls"].is_relevant:
        return "chitchat"
    return "rag"


def node_urgent_escalate(state: PipelineState) -> dict:
    """민감·긴급 민원: RAG/LLM 답변생성 없이 즉시 접수 확인만. 담당자에게 우선 전달."""
    rule = state["rule"]
    answer = (
        "안녕하세요. 긴급/민감 민원으로 접수되어 담당자에게 즉시 전달되었습니다.\n\n"
        f"{rule.department}에서 신속히 확인 후 회신드리겠습니다. 불편을 드려 죄송합니다."
    )
    return {"route": "urgent", "answer": answer, "answer_confidence": AnswerConfidence.PARTIAL,
            "docs": [], "llm_error": None}


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
            "answer_confidence": AnswerConfidence.INSUFFICIENT, "docs": [], "llm_error": None}


# --- RAG 경로: 검색 → 근거채점 → (재검색) → 답변생성 → 환각/적합성 채점 → (재생성) ---

def node_retrieve(state: PipelineState) -> dict:
    docs = retrieve(state["search_query"], state["cls"])
    return {"docs": docs, "route": "rag"}


def node_doc_grade(state: PipelineState) -> dict:
    docs = state["docs"]
    # score 가 명백히 바닥이면 LLM 채점도 아끼고 바로 관련없음 처리
    if _top_score(docs) < settings.no_evidence_threshold:
        return {"doc_relevant": False}
    return {"doc_relevant": grade_documents(state["text"], docs)}


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
    try:
        answer, conf = generate(state["text"], state["cls"], state["rule"], state["docs"])
        return {"answer": answer, "answer_confidence": conf, "llm_error": None}
    except LLMError as e:
        err = str(e)
        answer = fallback_answer(state["text"], state["cls"], state["rule"], state["docs"], reason=err)
        return {"answer": answer, "answer_confidence": AnswerConfidence.PARTIAL, "llm_error": err}


def node_hallucination_grade(state: PipelineState) -> dict:
    if state["llm_error"]:  # 이미 폴백 답변이면 채점 불필요
        return {"hallucination_ok": True}
    return {"hallucination_ok": grade_hallucination(state["answer"], state["docs"])}


def _route_after_hallucination(state: PipelineState) -> str:
    if state["hallucination_ok"]:
        return "answer_grade"
    if state["regenerate_count"] < _MAX_REGENERATE:
        return "bump_regenerate"
    return "answer_grade"  # 재시도 소진 → 일단 통과, finalize 에서 확신도 하향


def node_answer_grade(state: PipelineState) -> dict:
    if state["llm_error"]:
        return {"answer_ok": True}
    return {"answer_ok": grade_answer(state["text"], state["answer"])}


def _route_after_answer_grade(state: PipelineState) -> str:
    if state["answer_ok"]:
        return "finalize"
    if state["regenerate_count"] < _MAX_REGENERATE:
        return "bump_regenerate"
    return "finalize"  # 재시도 소진 → finalize 에서 확신도 하향


def node_bump_regenerate(state: PipelineState) -> dict:
    return {"regenerate_count": state["regenerate_count"] + 1}


def node_finalize(state: PipelineState) -> dict:
    """검증을 통과하지 못한 채 재시도가 소진된 답변은 확신도를 낮춰 담당자 확인을 유도."""
    if not state.get("hallucination_ok", True) or not state.get("answer_ok", True):
        if state["answer_confidence"] == AnswerConfidence.SUFFICIENT:
            return {"answer_confidence": AnswerConfidence.PARTIAL}
    return {}


# --- 그래프 구성 ---

def _build_graph():
    g = StateGraph(PipelineState)
    g.add_node("classify", node_classify)
    g.add_node("rule", node_rule)
    g.add_node("urgent_escalate", node_urgent_escalate)
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
    g.add_conditional_edges("rule", _route_after_rule, {
        "urgent": "urgent_escalate", "chitchat": "chitchat_decline", "rag": "retrieve",
    })
    g.add_edge("urgent_escalate", END)
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
        "answer": None, "answer_confidence": None, "llm_error": None, "route": "",
        "doc_relevant": False, "rewrite_count": 0, "hallucination_ok": True,
        "answer_ok": True, "regenerate_count": 0,
    }
    result: PipelineState = _graph.invoke(init)

    return InquiryResponse(
        original_text=text,
        classification=result["cls"],
        rule=result["rule"],
        retrieved=result["docs"] or [],
        answer_draft=result["answer"],
        answer_confidence=result["answer_confidence"],
        used_llm=settings.has_api_key and result["llm_error"] is None,
        llm_error=result["llm_error"],
    )