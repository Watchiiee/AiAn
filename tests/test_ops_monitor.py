"""
Ops 모니터링의 패턴 판정(_classify_pattern) 회귀테스트.

Z-5/Z-6에서 확인한 원칙 - "국한된 문제/광범위한 문제/특이사항 없음" 판정은
LLM이 아니라 코드가 결정론적으로 내린다. 이 테스트는 LLM 호출이 전혀
필요 없어 빠르고 안정적으로 돈다 - scripts/debug_ops_monitor_pilot.py의
3개 시나리오(A/B/C)를 그대로 회귀테스트로 옮긴 것.
"""
from AI.ops_monitor import aggregate_stats


def _trace(text, domain, category, rewrite=0, regenerate=0, confidence="sufficient", halluc_ok=True):
    return {
        "input": {"text": text},
        "output": {
            "text": text, "route": "rag",
            "cls": {"domain": domain, "category": category},
            "rewrite_count": rewrite, "regenerate_count": regenerate,
            "answer_confidence": confidence,
            "hallucination_ok": halluc_ok, "answer_ok": True,
        },
    }


def test_concentrated_category_issue_detected():
    """특정 카테고리(기타)에서만 재시도가 몰리면 '국한된 문제'로 판정해야
    한다(P2-29/30류 재현, 1차 파일럿에서 실제로 실패했던 케이스)."""
    traces = [_trace(f"기타질문{i}", "technical", "기타", rewrite=2, confidence="partial", halluc_ok=False)
              for i in range(8)]
    traces += [_trace(f"정상질문{i}", "admin", "교육", confidence="sufficient") for i in range(22)]

    stats = aggregate_stats(traces)

    assert not stats["pattern_verdict"].startswith("광범위")
    assert "국한" in stats["pattern_verdict"]
    assert "기타" in stats["pattern_verdict"]


def test_widespread_issue_detected():
    """대부분의 카테고리에서 고르게 재시도가 발생하면 '광범위한 문제'로
    판정해야 한다(R/S절 DYNAMIC_TOPK x all_or_nothing 회귀류 재현)."""
    categories = [("기술지원", "technical"), ("교육", "admin"), ("경력회원", "admin"),
                  ("공제사업", "admin"), ("전기안전관리자", "admin")]
    traces = []
    for i in range(30):
        cat, dom = categories[i % len(categories)]
        if i < 24:
            traces.append(_trace(f"문의{i}", dom, cat, rewrite=2, confidence="insufficient"))
        else:
            traces.append(_trace(f"문의{i}", dom, cat, confidence="sufficient"))

    stats = aggregate_stats(traces)

    assert "광범위" in stats["pattern_verdict"]


def test_no_false_alarm_on_quiet_day():
    """평범한 날(재시도 극소수, 카테고리당 1건 이하)엔 '특이사항 없음'으로
    판정해야 한다 - 과잉경보 방지가 이 테스트의 핵심(2차 파일럿에서 실제로
    실패했다가 코드-판단 분리로 해결된 부분)."""
    categories = [("기술지원", "technical"), ("교육", "admin"), ("경력회원", "admin"),
                  ("공제사업", "admin"), ("전기안전관리자", "admin"), ("기타", "admin")]
    traces = []
    for i in range(30):
        cat, dom = categories[i % len(categories)]
        if i in (3, 17):
            traces.append(_trace(f"문의{i}", dom, cat, rewrite=1, confidence="partial"))
        else:
            traces.append(_trace(f"문의{i}", dom, cat, confidence="sufficient"))

    stats = aggregate_stats(traces)

    assert "특이사항 없음" in stats["pattern_verdict"]
    assert "✅" in stats["pattern_label"]


def test_empty_traces_returns_total_zero():
    stats = aggregate_stats([])
    assert stats["total"] == 0


def test_output_none_does_not_crash():
    """트레이스 하나의 output이 비어있어도(처리 중 실패 등) 전체 집계가
    죽지 않아야 한다(방어적 접근)."""
    traces = [
        {"input": {"text": "정상질문"}, "output": {
            "text": "정상질문", "route": "rag", "cls": {"domain": "admin", "category": "교육"},
            "rewrite_count": 0, "regenerate_count": 0, "answer_confidence": "sufficient",
            "hallucination_ok": True, "answer_ok": True,
        }},
        {"input": {"text": "실패한질문"}, "output": None},
    ]

    stats = aggregate_stats(traces)

    assert stats["total"] == 2