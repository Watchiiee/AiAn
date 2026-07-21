"""
doc_grade 모드(all_or_nothing vs individual) 1차 소규모 비교 테스트.

전체 89개가 아니라, "동적top_k로 개선됐던 12개"(선별이 실제로 노이즈를 걷어내는지)
+ "motor 계열 대조군 5개"(원래 잘 되던 케이스를 individual 모드가 실수로
깨지 않는지)만 골라 저비용으로 먼저 이상 신호를 잡는다. 여기서 문제없으면
전체 골든셋(eval_golden_set 확장판)으로 2차 검증.

process_inquiry()가 아니라 pipeline._graph.invoke()를 직접 불러서, API 응답에는
없는 내부 상태(graded_docs, rewrite_count, regenerate_count)까지 전부 들여다본다.

실행 (레포 루트에서, venv 활성화 후 — 실제 CLOVA 호출이라 비용/시간 발생):
    python3 -m scripts.test_doc_grade_modes
"""
import os
import sys
import importlib

sys.path.insert(0, os.getcwd())

# (id, 도메인, 질문, 그룹) — 그룹: "개선사례"(동적top_k로 좋아졌던 것, individual이
# 여기서 노이즈를 잘 걸러내는지 봄) / "대조군"(원래 잘 되던 것, 실수로 깨지는지 봄)
TEST_CASES = [
    ("G04", "technical", "440V 델타결선 변압기는 왜 1상 접지를 못 하고, GPT 3차권선은 접지 안 해도 계전기가 동작하나요?", "개선사례"),
    ("M05", "technical", "간판에 무전기 쓰면 소용량 MCCB가 트립되는 거랑, 순간정전 때도 차단기가 떨어지는 게 같은 원인인가요?", "개선사례"),
    ("P2-06", "technical", "CT 2차를 열어놓으면 왜 위험한가요?", "개선사례"),
    ("P2-12", "technical", "22.9kV 선로를 저압용 클램프미터로 측정해도 되나요?", "개선사례"),
    ("P2-28", "technical", "역률계가 이상하게 고정되어 안 움직이는데 원인이 뭔가요?", "개선사례"),
    ("P2-39", "admin", "최초 경력신고를 하려면 제출서류와 절차는 어떻게 되나요?", "개선사례"),
    ("P2-40", "admin", "경력신고 처음 할 때 뭘 내야 하나요?", "개선사례"),
    ("P2-42", "admin", "컨소시엄 교육 누가 들을 수 있나요?", "개선사례"),
    ("P2-44", "admin", "감리실적 신고할 때 뭘 내야 하나요?", "개선사례"),
    ("P2-46", "admin", "안전관리 교육 어떻게 신청하나요?", "개선사례"),
    ("P2-49", "admin", "회원가입 절차는 어떻게 되나요?", "개선사례"),
    ("BP-07", "technical", "500kW 발전기가 자꾸 과부하로 멈추는 이유가 뭔가요", "개선사례"),
    ("MT01", "technical", "소화전 주모터(Y-△방식) 수동투입 시 회전하지 않고 웅~ 소리만 나다가 t초 후 회전하는데, 마그넷 고장인가요?", "대조군"),
    ("MT02", "technical", "모터 결선방식(380V 전용 / 220·380V 겸용 / 220V 전용)에 따라 Y-△ 기동 가능 여부와 소손 위험이 다른 이유는 무엇인가요?", "대조군"),
    ("MT03", "technical", "Y기동 걸 때 웅 소리만 나고 안 돌아가는데 왜 그런가요?", "대조군"),
    ("MT04", "technical", "380V 전용 모터랑 220V 겸용 모터를 Y-델타로 기동시켜도 되나요?", "대조군"),
    ("MT05", "technical", "회전방향이 반대로 돌고, 발전기 돌릴 때마다 벨트가 끊어지는데 상순서 문제인가요?", "대조군"),
]


def run_mode(mode: str) -> list[dict]:
    os.environ["RAG_DOC_GRADE_MODE"] = mode
    import BE.api.pipeline as pipeline
    importlib.reload(pipeline)  # 모듈 최상단 DOC_GRADE_MODE 상수를 다시 읽게

    print(f"\n{'='*80}\n모드: {mode}\n{'='*80}")
    rows = []
    for qid, domain, question, group in TEST_CASES:
        init = {
            "text": question, "search_query": question, "cls": None, "rule": None,
            "docs": None, "graded_docs": None, "answer": None, "answer_confidence": None,
            "llm_error": None, "route": "", "is_urgent": False, "urgent_reason": None,
            "doc_relevant": False, "rewrite_count": 0, "hallucination_ok": True,
            "answer_ok": True, "regenerate_count": 0,
        }
        result = pipeline._graph.invoke(init)

        n_full = len(result.get("docs") or [])
        n_graded = len(result.get("graded_docs") or [])
        conf = result.get("answer_confidence")
        conf_val = conf.value if hasattr(conf, "value") else conf

        row = {
            "id": qid, "group": group, "n_full": n_full, "n_graded": n_graded,
            "rewrite_count": result.get("rewrite_count", 0),
            "regenerate_count": result.get("regenerate_count", 0),
            "confidence": conf_val,
        }
        rows.append(row)
        print(f"[{group}][{qid}] 전체검색={n_full} 선택={n_graded} 재검색={row['rewrite_count']} "
              f"재생성={row['regenerate_count']} confidence={conf_val}")
    return rows


def run():
    rows_all = run_mode("all_or_nothing")
    rows_ind = run_mode("individual")

    print("\n" + "=" * 90)
    print("비교")
    print("=" * 90)
    print(f"{'id':<8}{'그룹':<8}{'all전체':<8}{'all재검색':<10}{'all conf':<12}"
          f"{'ind선택':<8}{'ind재검색':<10}{'ind conf':<12}")
    for a, i in zip(rows_all, rows_ind):
        print(f"{a['id']:<8}{a['group']:<8}{a['n_full']:<8}{a['rewrite_count']:<10}{str(a['confidence']):<12}"
              f"{i['n_graded']:<8}{i['rewrite_count']:<10}{str(i['confidence']):<12}")

    # --- 선택 개수 분포 (individual 모드) ---
    print("\n" + "=" * 90)
    print("individual 모드 선택 개수 분포")
    print("=" * 90)
    buckets = {"0개": 0, "1개": 0, "2~3개": 0, "4개 이상": 0}
    for r in rows_ind:
        n = r["n_graded"]
        if n == 0:
            buckets["0개"] += 1
        elif n == 1:
            buckets["1개"] += 1
        elif n <= 3:
            buckets["2~3개"] += 1
        else:
            buckets["4개 이상"] += 1
    for k, v in buckets.items():
        print(f"  {k}: {v}개 문항")
    print("\n주의: '0개'나 '1개'가 많으면 individual 모드가 과도하게 엄격하게 걸러내고 있다는")
    print("      신호일 수 있음(특히 대조군에서 나오면 문제) — 이 경우 프롬프트를 더 관대하게")
    print("      조정할 필요가 있음.")

    # --- confidence 비교 요약 ---
    def _conf_summary(rows):
        from collections import Counter
        return Counter(r["confidence"] for r in rows)

    print("\n" + "=" * 90)
    print("confidence 분포 비교")
    print("=" * 90)
    print("all_or_nothing:", dict(_conf_summary(rows_all)))
    print("individual    :", dict(_conf_summary(rows_ind)))


if __name__ == "__main__":
    run()