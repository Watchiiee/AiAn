"""
Adaptive RAG 채점기(grader) 모음.

각 함수는 독립된 짧은 LLM 호출로 하나의 판단만 한다 (역할 혼동 방지).
LLM 호출 실패나 파싱 실패 시 '보수적인 기본값'으로 처리한다 — 즉, 애매하면
"근거 부족/검증 실패/긴급 아님" 쪽으로 기울여서, 잘못된 정보를 그냥 통과시키거나
근거 없이 사람을 호출하기보다 안전한 쪽으로 처리한다.
"""
import json
import re

from AI.llm import call_llm, LLMError

from AI.prompts import (
    DOC_GRADER_SYSTEM, DOC_GRADER_SYSTEM_INDIVIDUAL, HALLUCINATION_GRADER_SYSTEM,
    ANSWER_GRADER_SYSTEM, QUERY_REWRITE_SYSTEM, URGENCY_GRADER_SYSTEM, QUERY_DECOMPOSE_SYSTEM,
)
from BE.core.config import settings
from BE.core.schemas import RetrievedDoc


def _strip_code_fence(raw: str) -> str:
    """CLOVA가 ```json ... ``` 으로 감싸서 줄 때가 있어 벗겨낸다 (classifier.py와 동일 문제)."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _safe_bool_call(system: str, user: str, key: str, default: bool) -> bool:
    """grader 공통 호출부. 실패하면 default(보수적 값)로."""
    try:
        raw = call_llm(settings.classifier_model, system, user, max_tokens=64)
    except LLMError:
        return default
    if raw is None:
        return default
    try:
        return bool(json.loads(_strip_code_fence(raw)).get(key, default))
    except (json.JSONDecodeError, ValueError, AttributeError):
        return default


def grade_documents(question: str, docs: list[RetrievedDoc]) -> bool:
    """검색된 문서가 질문에 답하기에 쓸모 있는지. 판단 실패 시 보수적으로 False(재검색 유도)."""
    if not docs:
        return False
    docs_text = "\n".join(f"- {d.content}" for d in docs)
    user = f"[질문] {question}\n\n[검색된 문서]\n{docs_text}"
    return _safe_bool_call(DOC_GRADER_SYSTEM, user, "relevant", default=False)


def grade_documents_individual(question: str, docs: list[RetrievedDoc]) -> list[int]:
    """
    검색된 문서 각각을 개별 판단해, 관련 있다고 판단한 것들의 인덱스(docs 리스트 기준)를
    반환한다. 판단 실패 시 보수적으로 빈 리스트(재검색 유도 — grade_documents와 동일한
    실패 시 정책).

    grade_documents()(전체를 하나로 묶어 true/false)와 병행 존재 — pipeline.py의
    node_doc_grade가 RAG_DOC_GRADE_MODE 환경변수로 둘 중 하나를 선택해 쓴다
    (하이브리드·동적top_k와 같은 단계적 도입 패턴, DECISION_LOG 참고).
    """
    if not docs:
        return []
    docs_text = "\n".join(f"[{i}] (검색점수={d.score}) {d.content}" for i, d in enumerate(docs))
    user = f"[질문] {question}\n\n[검색된 문서 목록]\n{docs_text}"
    try:
        raw = call_llm(settings.classifier_model, DOC_GRADER_SYSTEM_INDIVIDUAL, user, max_tokens=128)
    except LLMError:
        return []
    if raw is None:
        return []
    try:
        data = json.loads(_strip_code_fence(raw))
        selected = data.get("selected", [])
        # 인덱스 범위를 벗어나는 값(LLM이 잘못된 번호를 줄 경우)은 방어적으로 걸러냄
        return [i for i in selected if isinstance(i, int) and 0 <= i < len(docs)]
    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
        return []


def grade_hallucination(answer: str, docs: list[RetrievedDoc]) -> bool:
    """답변이 근거 문서에만 기반하는지. 판단 실패 시 보수적으로 False(재생성 유도)."""
    docs_text = "\n".join(f"- {d.content}" for d in docs)
    user = f"[근거 문서]\n{docs_text}\n\n[생성된 답변]\n{answer}"
    return _safe_bool_call(HALLUCINATION_GRADER_SYSTEM, user, "grounded", default=False)


def grade_answer(question: str, answer: str) -> bool:
    """답변이 질문의 핵심 요청을 다루는지. 판단 실패 시 보수적으로 False(재생성 유도)."""
    user = f"[질문] {question}\n\n[답변]\n{answer}"
    return _safe_bool_call(ANSWER_GRADER_SYSTEM, user, "addressed", default=False)


def rewrite_query(original_text: str) -> str:
    """검색이 잘 안 된 질문을 검색 친화적으로 재작성. 실패 시 원문 그대로 반환."""
    try:
        raw = call_llm(settings.classifier_model, QUERY_REWRITE_SYSTEM, original_text, max_tokens=128)
    except LLMError:
        return original_text
    if raw is None:
        return original_text
    try:
        rewritten = json.loads(_strip_code_fence(raw)).get("rewritten", "").strip()
        return rewritten or original_text
    except (json.JSONDecodeError, ValueError, AttributeError):
        return original_text


def check_urgency(text: str) -> tuple[bool, str | None]:
    """
    문의가 즉시 사람 개입이 필요한 긴급/민감 민원인지 독립적으로 판단한다.
    (분류 프롬프트에 같이 섞지 않고 별도 호출로 분리 — 여러 판단을 한 프롬프트에
    몰아넣으면 필드가 혼동됐던 전례가 있어, 판단 하나당 호출 하나 원칙을 지킨다.)
    단순 키워드 매칭이 아니라 문맥으로 판단하며, 판단 실패 시 보수적으로
    (False, None) — 근거 없이 긴급으로 몰아 사람을 호출하지 않는다.
    """
    try:
        raw = call_llm(settings.classifier_model, URGENCY_GRADER_SYSTEM, text, max_tokens=128)
    except LLMError:
        return False, None
    if raw is None:
        return False, None
    try:
        data = json.loads(_strip_code_fence(raw))
        is_urgent = bool(data.get("is_urgent", False))
        reason = (data.get("urgent_reason") or "").strip()
        if is_urgent and reason:
            return True, reason
        return False, None  # is_urgent=True인데 이유가 없으면 근거 부족으로 보고 기각
    except (json.JSONDecodeError, ValueError, AttributeError):
        return False, None


def decompose_query(text: str) -> list[str]:
    """
    문의 안에 서로 다른 주제의 질문이 여러 개 섞여 있으면 독립된 검색 질문들로
    분리한다. 분해할 필요가 없으면 원문 하나만 담긴 리스트를 반환한다.

    실측(M-4)으로 확인된 진짜 복합질문 비율은 3.8%로 낮은 편이라, "잘못 쪼개서
    없던 문제를 만드는 위험"이 이 기능의 가장 큰 리스크다. 그래서 파싱 실패나
    호출 실패 시에는 항상 "분해하지 않음"(원문 그대로 하나)으로 안전하게 폴백한다
    — 다른 grader들의 "보수적 기본값" 원칙과 같되, 여기서는 "분해 안 함"이
    보수적인 쪽이다.

    파싱은 classify_domain()에서 겪은 문제(CLOVA가 순수 JSON을 안 지키고 설명글을
    먼저 쓰는 경우가 있음)를 감안해 2단계로 방어한다: ① 순수 JSON, ② 실패하면
    "sub_questions" 배열 안의 문자열들을 정규식으로 직접 추출.
    """
    try:
        raw = call_llm(settings.classifier_model, QUERY_DECOMPOSE_SYSTEM, text, max_tokens=256)
    except LLMError:
        return [text]
    if raw is None:
        return [text]

    try:
        data = json.loads(_strip_code_fence(raw))
        sub_qs = data.get("sub_questions", [])
        cleaned = [q.strip() for q in sub_qs if isinstance(q, str) and q.strip()]
        return cleaned if cleaned else [text]
    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
        pass

    # 순수 JSON이 아니었던 경우: "sub_questions": [...] 배열 안의 문자열들을 정규식으로 추출
    match = re.search(r'"sub_questions"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
    if match:
        items = re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1))
        cleaned = [item.strip() for item in items if item.strip()]
        if cleaned:
            return cleaned

    return [text]  # 뭘 해도 못 찾으면 안전하게 "분해 안 함"