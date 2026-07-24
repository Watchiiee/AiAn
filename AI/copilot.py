"""
담당자 코파일럿(StaffPage 사이드바 대화형 도우미)의 컨텍스트 조합 로직.

파일럿 검증(scripts/debug_copilot_pilot.py)에서 쓴 컨텍스트 형식을 실제
InquiryRecord(DB에서 읽어온 값)로부터 그대로 재현한다. v1 범위는 "이미
계산되어 저장된 데이터를 설명하는 것"으로 한정한다(README 11절/설계 논의
참고) — 새로운 검색이 필요한 질문은 COPILOT_SYSTEM 프롬프트 안에서 정해진
문구로 거절하게 되어 있으므로, 이 모듈은 새 검색을 절대 수행하지 않는다.
"""
from typing import Any


def _doc_line(index: int, doc: dict) -> str:
    """검색문서 하나를 컨텍스트용 한 줄로 변환. retrieved_docs는 JSON 컬럼에서
    읽어온 dict 리스트이므로 .get()으로 접근한다(Pydantic 객체가 아님)."""
    selected = doc.get("selected", True)
    mark = "선택됨" if selected else "선택 안 됨"
    content = doc.get("content", "")
    source = doc.get("source", "")
    return f"  [{index}] ({mark}) {content} — 출처: {source}"


def build_copilot_context(record: Any) -> str:
    """
    InquiryRecord(SQLAlchemy 모델 인스턴스, 또는 동일한 속성을 가진 객체)로부터
    코파일럿 시스템 프롬프트 뒤에 붙일 컨텍스트 문자열을 만든다.

    record가 가져야 하는 속성: original_text, domain, category, inquiry_type,
    retrieved_docs(dict 리스트), answer_draft, answer_confidence.
    """
    docs = record.retrieved_docs or []
    docs_text = "\n".join(_doc_line(i, d) for i, d in enumerate(docs))
    if not docs_text:
        docs_text = "  (검색된 문서 없음)"

    category = record.category or "(미분류)"
    confidence = record.answer_confidence
    confidence = confidence.value if hasattr(confidence, "value") else confidence

    return f"""[원본 문의] {record.original_text}
[분류] {record.domain} / {category} / {record.inquiry_type}
[검색된 문서 전체]
{docs_text}
[생성된 답변] {record.answer_draft}
[확신도] {confidence}"""


def build_copilot_prompt(record: Any, question: str) -> str:
    """COPILOT_SYSTEM과 함께 call_llm()의 user 프롬프트로 넘길 최종 문자열."""
    return f"{build_copilot_context(record)}\n\n[담당자 질문] {question}"